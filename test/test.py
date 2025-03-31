from bs4 import BeautifulSoup
import requests
import json
from datetime import datetime, timedelta
from prettytable import PrettyTable


event_target = 'grdFAR$ctl19$ctl01'
viewstate_generator = 'FAC76EB7'
event_target_prev = 'drpArchival'
viewstate_generator_prev = 'E08232C2'
far_table_id = 'grdFAR'
gen_limit_table_id = 'grdFPISWH'


def scrape_far_holding(url, url_prev):
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    viewstate = get_viewstate(soup)
    event_validation = get_event_validation(soup)

    soup_prev = BeautifulSoup(requests.get(url_prev).content, 'html.parser')
    drp_archival = get_previous_date()
    viewstate_prev = get_viewstate(soup_prev)
    event_validation_prev = get_event_validation(soup_prev)

    # get cumulative diff
    payload_prev = get_payload_prev(drp_archival, event_validation_prev, viewstate_prev)
    diff, soup_prev = get_far_holdings_diff(payload_prev, soup, url_prev)

    # capture far changes
    payload = get_payload(event_validation, viewstate)
    payload['btnFAR'] = 'Export To Excel'
    payload_prev['__VIEWSTATE'] = get_viewstate(soup_prev)
    payload_prev['__EVENTVALIDATION'] = get_event_validation(soup_prev)
    payload_prev['btnFAR'] = 'Export To Excel'
    map_today = {}
    map_prev = {}
    map_today, map_prev = update_maps(map_today, map_prev, payload, payload_prev, url, url_prev, far_table_id)

    del payload['btnFAR']
    del payload_prev['btnFAR']
    payload['btnFPISWH'] = 'Export To Excel'
    payload_prev['btnFPISWH'] = 'Export To Excel'
    map_today, map_prev = update_maps(map_today, map_prev, payload, payload_prev, url, url_prev, gen_limit_table_id)

    # create difference table
    table_li = []
    head = ['Security Description', '   ', 'FPI Holding', '    ', 'D-o-D']
    for key in map_today.keys():
        if key in map_prev.keys():
            ind_diff = round(float(map_today.get(key)) - float(map_prev.get(key)), 2)
        if ind_diff != 0:
            li = [key, '   ', round(float(map_today.get(key)), 2), '    ', ind_diff]
            table_li.append(li)

    final_table = PrettyTable(head)
    table_li.sort(key=lambda x: x[-1], reverse=True)
    for li in table_li:
        final_table.add_row(li, divider=False)

    print(final_table.get_string())
    table_str = final_table.get_html_string()
    return diff, table_str


def update_maps(map_today, map_prev, payload, payload_prev, url, url_prev, table_id):
    table, page = get_table_and_page([], {}, payload, url, table_id)
    table_prev, page_prev = get_table_and_page([], {}, payload_prev, url_prev, table_id)
    if table is not None and table_prev is not None:
        rows_all = table.select('tr')
        rows_all_prev = table_prev.select('tr')
        for i in range(1, len(rows_all_prev) - 1):
            row_key = rows_all[i].select('td')[1].text
            map_today[row_key] = map_today.get(row_key, 0.0) + float(rows_all[i].select('td')[2].text)
            row_key_prev = rows_all_prev[i].select('td')[1].text
            map_prev[row_key_prev] = map_prev.get(row_key_prev, 0.0) + float(rows_all_prev[i].select('td')[2].text)
    return map_today, map_prev


def get_far_holdings_diff(payload_prev, soup, url_prev):

    # FAR Holdings | today
    table_home = soup.find('table', id=far_table_id)
    if table_home is not None:
        rows = table_home.select('tr')[-2]
        data = rows.select('td')[2]
        print('FAR Holdings | today', data.text)

    # FAR Holdings | yesterday
    headers = {}
    files = []
    table_home_prev, soup_prev = get_table_and_page(files, headers, payload_prev, url_prev, far_table_id)
    if table_home_prev is not None:
        rows = table_home_prev.select('tr')[-2]
        data_prev = rows.select('td')[2]
        print('FAR Holdings | yesterday ', data_prev.text)

    diff = float(data.get_text()) - float(data_prev.get_text())
    print('FAR Holdings cumulative difference: ', diff)
    return diff, soup_prev





def get_table_and_page(files, headers, payload_prev, url_prev, table_id):
    response_prev = requests.request('POST', url_prev, headers=headers, data=payload_prev, files=files)
    soup_prev = BeautifulSoup(response_prev.content, 'html.parser')
    table_home_prev = soup_prev.find('table', id=table_id)
    return table_home_prev, soup_prev


def get_event_validation(soup):
    return soup.find('input', id='__EVENTVALIDATION').get('value')


def get_viewstate(soup):
    return soup.find('input', id='__VIEWSTATE').get('value')


def get_payload_prev(drp_archival, event_validation_prev, viewstate_prev):
    payload_prev = {
        'drpArchival': drp_archival,
        '__VIEWSTATE': viewstate_prev,
        '__EVENTTARGET': event_target_prev,
        '__VIEWSTATEGENERATOR': viewstate_generator_prev,
        '__EVENTVALIDATION': event_validation_prev,
        '__VIEWSTATEENCRYPTED': '',
        '__EVENTARGUMENT': '',
        '__LASTFOCUS': '',
    }
    return payload_prev


def get_payload(event_validation, viewstate):
    payload = {
        '__EVENTTARGET': event_target,
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': viewstate,
        '__VIEWSTATEGENERATOR': viewstate_generator,
        '__VIEWSTATEENCRYPTED': '',
        '__EVENTVALIDATION': event_validation,
    }
    return payload


def get_previous_date(date, holidays):
    given_date = datetime.strptime(str(date), '%Y-%m-%d %H:%M:%S.%f')
    day_of_week = (given_date.weekday() + 1) % 7  # Convert Sunday from 6 to 0
    if day_of_week == 1:
        previous_date = date - timedelta(3)
        previous_date = datetime.strftime(previous_date, '%d-%b-%Y')
    else:
        previous_date = date - timedelta(1)
        previous_date = datetime.strftime(previous_date, '%d-%b-%Y')
    if previous_date in holidays:
        return get_previous_date(date - timedelta(1), holidays)
    return previous_date


if __name__ == "__main__":
    with open('../holidays.json', 'r') as f:
        holidays = json.load(f)['holidays']
        holidays = set(holidays)
        # print(get_previous_date(datetime.now(), holidays))
        today = datetime.strftime(datetime.now(), '%d-%b-%Y')
        if today in holidays:
            print("don't run")

    # scrape_far_holding("https://old.ccilindia.com/FPIHome.aspx", "https://old.ccilindia.com/FPI_ARCV.aspx")

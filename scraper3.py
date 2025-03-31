import requests
import constants
from bs4 import BeautifulSoup
from prettytable import PrettyTable, MSWORD_FRIENDLY
# from dynamodb import update_t1_unconfirmed, get_previous_t1_unconfirmed
from datetime import datetime


t1_standard_unconfirmed_table_id = "grdNDSOMUNReg"
t1_odd_unconfirmed_table_id = "grdNDSOMUNOL"
t2_standard_unconfirmed_table_id = "grdNDSOMUNReg"
t2_odd_unconfirmed_table_id = "grdNDSOMUNOL"
t2_standard_confirmed_table_id = "grdNDSOMReg"
t2_odd_confirmed_table_id = "grdNDSOMOL"
STANDARD = "standard"
ODD = "odd"
CONFIRMED = "confirmed"
UNCONFIRMED = "unconfirmed"
T1 = "t+1"
T2 = "t+2"
viewstate_generator_map = {T2: "44864614"}


def get_table_and_total():
    soup_t1 = BeautifulSoup(requests.get(constants.T1_TRADE_URL).content, "html.parser")
    soup_t2 = BeautifulSoup(requests.get(constants.T2_TRADE_URL).content, "html.parser")

    standard_unconfirmed_t1_deals, standard_unconfirmed_t1_total = get_deals_and_total(soup_t1, t1_standard_unconfirmed_table_id, constants.T1_UNCONFIRMED_DEAL_URL, STANDARD, UNCONFIRMED, T1)
    odd_unconfirmed_t1_deals, odd_unconfirmed_t1_total = get_deals_and_total(soup_t1, t1_odd_unconfirmed_table_id, constants.T1_UNCONFIRMED_DEAL_URL, ODD, UNCONFIRMED, T1)
    standard_unconfirmed_t2_deals, standard_unconfirmed_t2_total = get_deals_and_total(soup_t2, t2_standard_unconfirmed_table_id, constants.T2_UNCONFIRMED_DEAL_URL, STANDARD, UNCONFIRMED, T2)
    odd_unconfirmed_t2_deals, odd_unconfirmed_t2_total = get_deals_and_total(soup_t2, t2_odd_unconfirmed_table_id, constants.T2_UNCONFIRMED_DEAL_URL, ODD, UNCONFIRMED, T2)
    standard_confirmed_t2_deals, standard_confirmed_t2_total = get_deals_and_total(soup_t2, t2_standard_confirmed_table_id, constants.T2_CONFIRMED_DEAL_URL, STANDARD, CONFIRMED, T2)
    odd_confirmed_t2_deals, odd_confirmed_t2_total = get_deals_and_total(soup_t2, t2_odd_confirmed_table_id, constants.T2_CONFIRMED_DEAL_URL, ODD, CONFIRMED, T2)
    total = standard_unconfirmed_t2_total + odd_unconfirmed_t2_total + standard_confirmed_t2_total + odd_confirmed_t2_total

    today = datetime.now().strftime('%Y-%m-%d')
    security_map = {}
    standard_unconfirmed_t1_total = get_total_and_update_map(security_map, standard_unconfirmed_t1_deals, today, STANDARD)
    odd_unconfirmed_t1_total = get_total_and_update_map(security_map, odd_unconfirmed_t1_deals, today, ODD)
    total += standard_unconfirmed_t1_total + odd_unconfirmed_t1_total

    return 0


def denormalize_deals_map(final_list_of_deals, deals, settlement_type):
    if deals is not None:
        for key, values in dict.items():
            for value in values:
                final_list_of_deals.append([settlement_type, key] + value)


def get_total_and_update_map(security_map, deals, today, lot_type):
    total = 0
    if deals is not None:
        for security in deals:
            deal_amount = 0
            for deal in deals[security]:
                deal_amount = deal_amount + float(deal[1])
            security_map[security] = [str(round(deal_amount, 2)), lot_type]
            total = total + deal_amount
        prev_security_map = get_previous_t1_unconfirmed(today)

        for security in prev_security_map:
            if security not in security_map and prev_security_map[security][1] is lot_type:
                security_map[security] = prev_security_map[security]
                total = total + float(prev_security_map[security])
    return total


def get_deals_and_total(soup, table_id, url, lot_type, status, settlement_type):
    table = soup.find('table', id=table_id)
    if table is not None:
        number_of_pages = get_number_of_pages(table)
        all_tr_tags = table.find_all('tr')
        relevant_rows = all_tr_tags[1:-2]
        sec_last_tr = all_tr_tags[-2]
        total = float(sec_last_tr.find_all('td')[-1].get_text())
        if number_of_pages > 0 and (status is CONFIRMED):
            deals = get_deals_for_pages(soup, number_of_pages, table_id, relevant_rows, url, lot_type, status, settlement_type)
            return deals, total
        else:
            deals = get_deals_for_rows(relevant_rows, url, lot_type, status, settlement_type)
            return deals, total
    return None, 0.00


def get_number_of_pages(table):
    last_tr_tag = table.find_all('tr')[-1]
    last_td_tag = last_tr_tag.find_all('td')[-1]
    last_a = last_td_tag.find('a')
    if last_a is None:
        return 0
    last_a = last_td_tag.find_all('a')[-1]
    href_value = last_a.get_text()
    return int(href_value)


def get_deals_for_rows(rows, url, lot_type, status, settlement_type):
    security_description_list = []
    security_to_tr_tag_map = {}
    if rows is not None:
        for item in rows:
            security_description_list.append(item.select('td')[0].text.strip())
        print(f"{settlement_type}, {lot_type}, {status} with securities: {security_description_list}")

        headers = {}
        files = []
        params = get_params(lot_type, status)

        for i in security_description_list:
            if status is UNCONFIRMED:
                params['UNCT_IST_DESC'] = i
                table_id = "grdUNDTLS"
            else:
                params["ISMT_IDNT"] = i
                table_id = "grdIT"
            response = requests.request('GET', url, headers=headers, params=params, files=files)
            soup = BeautifulSoup(response.content, "html.parser")

            deal_table = soup.find('table', id=table_id)
            if deal_table is None:
                print(f"deal table is none for {settlement_type}, {lot_type}, {status}")
                return None
            all_tr_tags = deal_table.find_all('tr')
            result_tr_tags = all_tr_tags[1:-2]
            security_to_tr_tag_map[i] = result_tr_tags
        security_to_deal_map = {}

        for key, values in security_to_tr_tag_map.items():
            for value in values:
                td_tags = value.find_all('td')
                extracted_values = [td.text.strip() for td in td_tags]
                if key in security_to_deal_map:
                    security_to_deal_map[key].append(extracted_values)
                else:
                    security_to_deal_map[key] = [extracted_values]
        return security_to_deal_map
    return None


def get_params(lot_type, status):
    if lot_type is ODD and status is UNCONFIRMED:
        params = {
            'UNCT_IST_DESC': '',
            'BOOK_INDC': 'ODDX',
        }
    elif lot_type is STANDARD and status is UNCONFIRMED:
        params = {
            'UNCT_IST_DESC': '',
            'BOOK_INDC': 'RGLR',
        }
    elif lot_type is STANDARD and status is CONFIRMED:
        params = {
            "ISMT_IDNT": "",
            "MRKT_INDC": "CONT",
            "BOOK_INDC": "RGLR"
        }
    elif lot_type is ODD and status is CONFIRMED:
        params = {
            "ISMT_IDNT": "",
            "MRKT_INDC": "CONT",
            "BOOK_INDC": "ODDX"
        }
    return params


def get_deals_for_pages(soup, number_of_pages, table_id, relevant_rows, deal_url, lot_type, status, settlement_type):
    security_to_deal_map = get_deals_for_rows(relevant_rows, deal_url, lot_type, status, settlement_type)
    viewstate = soup.find('input', id="__VIEWSTATE").get('value')
    event_validation = soup.find('input', id="__EVENTVALIDATION").get('value')
    event_target = table_id + "$ctl09$ctl0"
    headers = {}
    files = []
    payload = {
        "__EVENTTARGET": event_target + "1",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": viewstate,
        "__VIEWSTATEGENERATOR": viewstate_generator_map[settlement_type],
        "__VIEWSTATEENCRYPTED": "",
        "__EVENTVALIDATION": event_validation,
    }
    for i in range(1, int(number_of_pages)):
        resp = requests.request('POST', constants.T2_TRADE_URL, headers=headers, data=payload, files=files)
        soup = BeautifulSoup(resp.content, "html.parser")
        table = soup.find('table', id=table_id)
        all_tr_tags = table.find_all('tr')
        relevant_rows = all_tr_tags[1:-2]
        deal_map_from_pages = get_deals_for_rows(relevant_rows, deal_url, lot_type, status, settlement_type)
        security_to_deal_map.update(deal_map_from_pages)
        payload["__EVENTTARGET"] = event_target + str(i - 1)
        payload["__VIEWSTATE"] = soup.find('input', id="__VIEWSTATE").get('value')
        payload["__EVENTVALIDATION"] = soup.find('input', id="__EVENTVALIDATION").get('value')
    return security_to_deal_map


if __name__ == "__main__":
    get_table_and_total()





from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta

url = "https://www.ccilindia.com/FPIHome.aspx"
url_prev = "https://www.ccilindia.com/FPI_ARCV.aspx"
yesterday = datetime.now() - timedelta(1)
yesterday = datetime.strftime(yesterday, '%d-%b-%Y')

html = requests.get(url)
soup = BeautifulSoup(html.content, "html.parser")
soup_prev = BeautifulSoup(requests.get(url_prev).content, "html.parser")
#print(soup.prettify())

drpArchival = yesterday
__VIEWSTATE = soup_prev.find('input', id="__VIEWSTATE").get('value')
__EVENTVALIDATION = soup_prev.find('input', id="__EVENTVALIDATION").get('value')
__EVENTTARGET = "drpArchival"
__VIEWSTATEGENERATOR = "E08232C2"
__VIEWSTATEENCRYPTED = ""
__EVENTARGUMENT = ""
__LASTFOCUS = ""

headers = {}
payload = {'drpArchival': drpArchival,
'__VIEWSTATE': __VIEWSTATE,
'__EVENTTARGET': 'drpArchival',
'__VIEWSTATEGENERATOR': 'E08232C2',
'__EVENTVALIDATION': __EVENTVALIDATION,
'__VIEWSTATEENCRYPTED': '',
'__EVENTARGUMENT': '',
'__LASTFOCUS': ''
}
files = [

]
response = requests.request('POST',url_prev,headers=headers,data=payload, files=files)



#FAR Holdings | today
table = soup.find('table',id='grdFAR')
if(table != None):
  rows = table.select('tr')[-2]
  data = rows.select('td')[2]
  print(data.text)

soup_prev1 = BeautifulSoup(response.content, "html.parser")
#FAR Holdings | yesterday
table_prev = soup_prev1.find('table',id='grdFAR')
if(table != None):
  rows = table.select('tr')[-2]
  data_prev = rows.select('td')[2]
  print(data_prev.text)
diff = float(data.get_text()) - float(data_prev.get_text())
print(diff)
if(diff != 0):
  rows_all_prev = table_prev.select('tr')
  rows_all = table.select('tr')
  li = []
  print("length=", len(rows_all_prev))
  for i in range(1,len(rows_all_prev)-2):
    if( rows_all[i].select('td')[2].text != rows_all_prev[i].select('td')[2].text):
      li.append(str(rows_all[i].select('td')[0].text))
  print(li)


    
    


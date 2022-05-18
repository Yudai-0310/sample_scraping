##########################################
# ディレクトリ構成は以下
# -- 2015_data/
#      |-- tmp_data
#      |-- data
##########################################

import os
import glob
import shutil
import time
import pytz
import datetime

import warnings
warnings.simplefilter('ignore')

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait       
from selenium.webdriver.common.keys import Keys

from bs4 import BeautifulSoup

def print_now():
    now = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))
    print(now)


##########################################
# Config
##########################################
page_num = 3 # 取得したいページ数
home_dir = '/Users/uenoyuudai/Downloads/2015_data/'
output_tmp_path = f'{home_dir}tmp_data/' # ダウンロード完了までファイルを置いておくパス(ここは絶対パス、相対パスだとダウンロードが完了しない)
output_path = f'{home_dir}data/' # ダウンロード完了したらファイルを移動してくる移動先のパス
chromedriver_path = '/Users/uenoyuudai/Desktop/chromedriver' # chromedriverのパス
url = 'https://www.e-stat.go.jp/gis/statmap-search?page=1&type=2&aggregateUnitForBoundary=A&toukeiCode=00200521&toukeiYear=2015&serveyId=A002005212015&coordsys=1&format=shape&datum=2000' # スクレイピングしたいURL
timeout_second = 30 # ファイルのダウンロードを待つ最長時間


##########################################
# スクレイピングの諸設定
##########################################
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_experimental_option('prefs', {'download.default_directory':output_tmp_path})

driver = webdriver.Chrome(chromedriver_path, options=options)
driver.get(url)
time.sleep(3)

##########################################
# 処理を関数化
##########################################
def download_data(driver):

    # メインページ（上記で定義したURLのページ）の情報を取得
    html = driver.page_source.encode('utf-8')
    bsObj = BeautifulSoup(html, "html.parser")
    table = bsObj.find('div', class_='stat-resorce_list-body')
    rows = table.findAll("div")

    print_now()

    # 県ごとにループ
    for i, row in enumerate(rows):
        
        # 1ページにつき20県分あるので21回目のループでbreak
        if i == 20:
            break

        # 県名情報を取得するために、aタグの部分を抽出する
        elem = row.find(['a'])
        # 県名を取得            
        pref_name = elem.find(['li']).get_text()
        print(f'{i+1}県目:{pref_name}')

        # 県名のディレクトリを作成
        pref_path = f'{home_dir}{pref_name}'
        if not os.path.isdir(pref_path):
            os.makedirs(pref_path)

        # 「XX 県名」のURLを取得
        detail = driver.find_element_by_css_selector(f"#main > section > div.js-search-detail > div > div > article:nth-child({i+1}) > div > ul > a > li:nth-child(1)")

        # オーバーレイ要素の考慮しつつクリック
        webdriver.ActionChains(driver).key_down(Keys.COMMAND).move_to_element(detail).click(detail).perform()
        time.sleep(2)
        # print('タブの個数:', len(driver.window_handles))

        # ダウンロードページへタブを遷移
        try:
            WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) >= 2)
            driver.switch_to.window(driver.window_handles[1])
            time.sleep(3)
            print(f"{pref_name}のダウンロードページへ遷移した")
            print(driver.current_url)

        except TimeoutException:
            print(f'{pref_name}のダウンロードページへ遷移できなかった')
            webdriver.ActionChains(driver).move_to_element(detail).click(detail).perform()
            WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) >= 2)
            driver.switch_to.window(driver.window_handles[1])
            time.sleep(1)

        # ダウンロードページが何ページあるか取得
        num_download_page = driver.find_element_by_css_selector("#main > section > div:nth-child(4) > div > div.stat-paginate-index.rig.js-paginate-index").text
        num_download_page = int(num_download_page[:-3].split('/')[1]) # 「1/3ページ」のようになっている場合、「3」を取得
        print(f'{pref_name}のダウンロードページのページ数:{num_download_page}')

        # ダウンロードページのページ数分だけループを回す
        for page in range(1, num_download_page+1):

            # ダウンロードページの情報を再度取得
            html_2 = driver.page_source.encode('utf-8')
            bsObj_2 = BeautifulSoup(html_2, "html.parser")
            div_2 = bsObj_2.find('div', class_='stat-resorce_list-body')
            rows_2 = div_2.findAll("div")

            # 市区町村の分だけループを回す
            for j, row2 in enumerate(rows_2):
                
                # ダウンロードボタンをクリック
                try:
                    # 市区町村名を取得するためにulタグの部分を取得
                    elem2 = row2.find(['ul'])   
                    # 市区町村名を取得        
                    city_name = elem2.find(['li']).get_text()

                    # ダウンロードボタンをクリック
                    print(f'{i+1}県目({pref_name})の{page}ページ目の{j+1}つ目の市区町村({city_name})をダウンロード')
                    download_btn = driver.find_element_by_css_selector(f"#main > section > div.js-search-detail > div > div > article:nth-child({j+1}) > div > ul > li:nth-child(3) > a")            
                    download_btn.click()
                    time.sleep(2)

                    # クリック後、ダウンロードが完了するまで待つ
                    for i in range(timeout_second + 1):
                        # list of file path を取得
                        list_files = glob.glob(f'{output_tmp_path}/*.*')

                        # ファイルが存在する場合
                        if len(list_files) > 0:

                            assert len(list_files) == 1, 'ダウンロードするディレクトリのファイル数が1ではない'

                            file_path = list_files[0]

                            # 拡張子の抽出
                            extension_name = os.path.splitext(file_path)[1]

                            # 拡張子が crdownload ではない場合、ダウンロード完了したから待機を抜ける
                            if ".crdownload" not in extension_name:
                                time.sleep(2)
                                break

                        # 指定時間待っても crdownload 以外のファイルが確認できない場合エラー
                        if i >= timeout_second:
                            print(f'{i+1}県目({pref_name})の{page}ページ目の{j+1}つ目の市区町村({city_name})をダウンロードできなかった!!!!!!!')

                        # 一秒待つ
                        time.sleep(1)

                    # ダウンロードボタンを押すとタブが増えてしまうから閉じておく
                    driver.switch_to.window(driver.window_handles[2])
                    driver.close()
                    driver.switch_to.window(driver.window_handles[1])

                except NoSuchElementException:
                    print(f'{i+1}県目({pref_name})の{page}ページ目の{j+1}つ目の市区町村({city_name})は見つからず')
                except AttributeError:
                    print(f'{i+1}県目({pref_name})の{page}ページ目の{j+1}つ目の市区町村({city_name})は存在せず')
                    break

                # ファイルを移動
                shutil.move(file_path, output_path)

                # 1市区町村だけやりたい場合
                break
            
            # 最終ページでない場合、次ページへ遷移
            if page != num_download_page:
                element = driver.find_element_by_css_selector("#main > section > div:nth-child(6) > div > div.stat-paginate-list.js-page_current.lef > span.stat-paginate-next.js-gisdownload-tabindex")
                element.click()
                time.sleep(2)
        
        # ダウンロードページを閉じる
        driver.close()
        time.sleep(2)

        # メインページへ遷移
        driver.switch_to.window(driver.window_handles[0])
        time.sleep(2)

        # ファイルを移動
        for p in glob.glob(f'{output_path}*.zip'):
            shutil.move(p, f'{home_dir}{pref_name}/')

        print("")

        # 1県だけやりたい場合
        # break

    print_now()


##########################################
# 実行
##########################################
for i in range(page_num):

    print(f'メインページの{i+1}ページ目を開始')

    download_data(driver)

    # 最終ページでない場合、次ページへ遷移
    if i != page_num:
        element = driver.find_element_by_css_selector("#main > section > div:nth-child(6) > div > div.stat-paginate-list.js-page_current.lef > span.stat-paginate-next.js-gisdownload-tabindex")
        element.click()

    time.sleep(2)

    print('')

    # 1ページ目だけやりたい場合
    break

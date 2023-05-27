from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from seleniumwire import webdriver

from tqdm.auto import tqdm
import pandas as pd
import argparse
import yt_dlp
import pytube
import time


KEYWORD = "Selenium automation with Python"
MAX_SCROLLS = 300
OUTPUT_FILENAME = "output1"
OUTPUT_FILEFORMAT = "xlsx"
HEADLESS = True

def initialize_driver(options: Options) -> webdriver.Firefox:
    """
    Initialize and return a Firefox webdriver instance with provided options.
    """
    driver = webdriver.Chrome(options=options, service=Service(ChromeDriverManager().install()))
    return driver

def get_webdriverOptions() -> Options:
    """
    returns a webdriver options object with the required options set
    """
    options = Options()
    user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
    options.add_argument(f'user-agent={user_agent}')
    options.add_argument("--incognito")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins-discovery")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-dev-shm-usage")
    if HEADLESS:
        options.add_argument('--headless')
        
    return options
    
def get_video_info(video_url):
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'skip_download': True,
        'getduration': True,
        'getid': True,
        'getdescription': True,
        'getuploaddate': True
    }
    max_tries = 3
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        while max_tries > 0:
            try:
                info_dict = ydl.extract_info(video_url, download=False)
                duration = info_dict.get('duration')
                video_id = info_dict.get('id')
                channel_id = info_dict.get('channel_id')
                description = info_dict.get('description')
                upload_date = info_dict.get('upload_date')
                if duration and video_id and channel_id and description and upload_date:
                    minutes, seconds = divmod(duration, 60)
                    return {
                        'duration': f'{minutes:02d}:{seconds:02d}',
                        'video_id': video_id,
                        'channel_id': channel_id,
                        'description': description,
                        'upload_date': upload_date
                    }
            except (yt_dlp.DownloadError,AttributeError):
                pass
            max_tries-=1
    
    return None


def search_youtube_videos(driver: webdriver.Firefox, keyword: str, max_scrolls: int) -> None:
    """
    Search YouTube for videos using the provided keyword, and scroll down the page to load more videos.
    """
    
    driver.get(f'https://www.youtube.com/results?search_query={keyword}')

    wait = WebDriverWait(driver, 60)
    wait.until(EC.presence_of_element_located((By.ID, "contents")))

    last_height = driver.execute_script("return document.documentElement.scrollHeight")
    scrolls = 0 
    print("Scrolling down the page...")
    while scrolls < max_scrolls:
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(5)
        new_height = driver.execute_script("return document.documentElement.scrollHeight")
        try:
            if new_height == last_height and WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "message"))):
                break
        except TimeoutException:
            continue
        
        last_height = new_height
        scrolls+=1
        

def scrape_video_data(driver: webdriver.Firefox) -> dict:
    """
    Scrape video data from the current YouTube search results page.
    """
    youtube_data = []
    for result in tqdm(driver.find_elements(By.CSS_SELECTOR, '.text-wrapper.style-scope.ytd-video-renderer'),desc="Processing", unit="video"):
        
        link = result.find_element(By.CSS_SELECTOR, '.title-and-badge.style-scope.ytd-video-renderer a').get_attribute('href')
        title = result.find_element(By.CSS_SELECTOR, '.title-and-badge.style-scope.ytd-video-renderer').text
        views = result.find_element(By.CSS_SELECTOR, '.style-scope ytd-video-meta-block').text.split('\n')[0]

        video_info = get_video_info(link)
        
        if video_info:
            vid_duration = video_info['duration']
            channelid = video_info['channel_id']
            video_id = video_info['video_id']
            dt_posted = video_info['upload_date']
            description = video_info['description']
        else:
            yt_master = pytube.YouTube(link)
            try:
                vid_duration = pytube.YouTube(link).length
                channelid = pytube.YouTube(link).channel_id
            except:
                vid_duration = None
                channelid = None
            try:
                video_id = yt_master.video_id
            except:
                video_id = None
            try:
                description = yt_master.description
            except:
                description = None
            try:
                dt_posted = yt_master.publish_date.strftime("%Y-%m-%d %H:%M:%S")
            except:
                dt_posted = None
            
        youtube_data.append({

            "Channel ID" : channelid,
            "Video ID" : video_id,
            "Youtube Link" :link,
            "Video Title" : title,
            "Description" : description,
            "Dt Posted": dt_posted,              
            "Views Count": views ,
            "Duration":vid_duration
        })

    return youtube_data

def save_data(data):

    df = pd.DataFrame(data).drop_duplicates()
    if OUTPUT_FILEFORMAT == 'csv':
        df.to_csv(f'{OUTPUT_FILENAME}.{OUTPUT_FILEFORMAT}', index=False)
    else:
        df.to_excel(f'{OUTPUT_FILENAME}.{OUTPUT_FILEFORMAT}', index=False)

if __name__=="__main__":
    
    print("Welcome to Youtube Data Scraper")
    parser = argparse.ArgumentParser(description='Data Scraping Script')
    parser.add_argument('--keyword', type=str, help='Keyword for scraping')
    parser.add_argument('--max-scrolls', type=int, help='Maximum number of scrolls')
    parser.add_argument('--output-filename', type=str, help='Output filename')
    parser.add_argument('--output-fileformat', type=str, help='Output file format')
    parser.add_argument('--headless', action='store_true', help='Enable headless mode')

    args = parser.parse_args()

    # Check if arguments are provided through command-line
    if args.keyword:
        KEYWORD = args.keyword
    if args.max_scrolls:
        MAX_SCROLLS = args.max_scrolls
    if args.output_filename:
        OUTPUT_FILENAME = args.output_filename
    if args.output_fileformat:
        OUTPUT_FILEFORMAT = args.output_fileformat
    if args.headless is not None:
        HEADLESS = args.headless
    
    print("Starting to Scrape....")
    print(f"Keyword : {KEYWORD}\n Max Scrolls : {MAX_SCROLLS}\n Output Filename : {OUTPUT_FILENAME}\n Output File Format : {OUTPUT_FILEFORMAT}\n Headless : {HEADLESS}")
    options = get_webdriverOptions()
    print("Initializing Driver....")
    driver = initialize_driver(options=options)
    print("Driver Initialized....")
    
    print("Searching Youtube Videos....")
    search_youtube_videos(driver=driver, keyword=KEYWORD, max_scrolls=MAX_SCROLLS)
    print("Search Completed....")
    
    print("Scraping Video Data....")
    youtube_data = scrape_video_data(driver=driver)
    print("Scraping Completed....")
    
    print(f"Saving Data to {OUTPUT_FILEFORMAT}....")
    save_data(data=youtube_data)
    print(f"Data Saved to {OUTPUT_FILEFORMAT}....")
    

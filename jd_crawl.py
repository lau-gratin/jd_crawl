import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random
import json
from selenium.webdriver.common.action_chains import ActionChains
import os

class JDReviewSpider:
    def __init__(self):
        """初始化爬虫类"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.base_url = 'https://www.jd.com'
        
    def init_driver(self):
        """初始化undetected_chromedriver"""
        print("正在初始化浏览器驱动...")
        try:
            options = uc.ChromeOptions()
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--lang=zh-CN')
            
            # 添加版本兼容性处理
            self.driver = uc.Chrome(
                options=options,
                version_main=123  # 指定与当前Chrome版本匹配的版本号
            )
            print("浏览器驱动初始化成功")
            
        except Exception as e:
            print(f"浏览器驱动初始化失败: {str(e)}")
            raise

    def login(self):
        """使用扫码登录京东账号"""
        try:
            print("正在尝试扫码登录...")
            
            # 打开京东登录页
            self.driver.get("https://passport.jd.com/new/login.aspx")
            
            # 使用显式等待
            wait = WebDriverWait(self.driver, 10)
            
            # 确保二维码加载完成
            print("等待二维码加载...")
            qr_code = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qrcode-img")))
            
            print("请使用京东 APP 扫描二维码登录...")
            
            # 等待登录成功
            while True:
                time.sleep(2)
                current_url = self.driver.current_url
                if 'passport.jd.com' not in current_url:
                    print("扫码登录成功！")
                    break
                
            # 保存cookies
            with open('jd_cookies.json', 'w') as f:
                json.dump(self.driver.get_cookies(), f)
                
        except Exception as e:
            print(f"登录失败: {str(e)}")
            print("当前页面标题:", self.driver.title)
            print("当前URL:", self.driver.current_url)
            raise

    def get_reviews(self, product_url, max_pages=1000):
        """获取商品评论信息"""
        reviews_data = []
        try:
            print(f"正在访问页面: {product_url}")
            self.driver.get(product_url)
            time.sleep(5)
            
            # 切换到评论tab
            try:
                comment_tab = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "li.tab-item[data-anchor='#comment']"))
                )
                comment_tab.click()
                time.sleep(2)
            except Exception as e:
                print(f"切换到评论tab失败: {str(e)}")
            
            page = 0
            while page < max_pages:
                page += 1
                print(f"\n正在爬取第 {page} 页评论...")
                
                # 等待评论区域加载
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "comment-item"))
                )
                
                # 获取评论列表
                comments = self.driver.find_elements(By.CLASS_NAME, "comment-item")
                if not comments:
                    print("没有找到更多评论，结束爬取")
                    break
                    
                print(f"当前页面找到 {len(comments)} 条评论")
                
                # 提取当前页面的评论
                for comment in comments:
                    try:
                        # 获取用户ID
                        user_id = comment.get_attribute("data-guid")
                        
                        # 获取用户信息
                        user_info = comment.find_element(By.CLASS_NAME, "user-info")
                        try:
                            user_level = comment.find_element(By.CLASS_NAME, "user-level").text
                        except:
                            user_level = ""
                        
                        # 获取评论内容
                        comment_text = comment.find_element(By.CLASS_NAME, "comment-con").text
                        
                        # 获取评论星级
                        try:
                            star_div = comment.find_element(By.CSS_SELECTOR, "div[class^='comment-star star']")
                            # 从class名称中提取星级数字
                            star_class = star_div.get_attribute("class")
                            comment_star = int(star_class.split("star")[-1])
                        except:
                            comment_star = 0
                        
                        # 获取订单信息
                        order_info = {}
                        try:
                            order_info_div = comment.find_element(By.CLASS_NAME, "order-info")
                            spans = order_info_div.find_elements(By.TAG_NAME, "span")
                            if spans:
                                order_info = {
                                    '商品型号': spans[0].text if len(spans) > 0 else "",
                                    '购买时间': spans[3].text if len(spans) > 3 else "",
                                    '购买地点': spans[4].text if len(spans) > 4 else ""
                                }
                        except:
                            pass
                        
                        # 获取评论图片（如果有的话）
                        images = []
                        try:
                            pic_list = comment.find_element(By.CLASS_NAME, "J-pic-list")
                            image_elements = pic_list.find_elements(By.TAG_NAME, "img")
                            images = [img.get_attribute("src") for img in image_elements]
                        except:
                            pass
                        
                        review_data = {
                            '用户ID': user_id,
                            '用户等级': user_level,
                            '评论内容': comment_text,
                            '评分': comment_star,
                            '商品型号': order_info.get('商品型号', ''),
                            '购买时间': order_info.get('购买时间', ''),
                            '购买地点': order_info.get('购买地点', ''),
                            '评论图片': images
                        }
                        
                        reviews_data.append(review_data)
                        
                    except Exception as e:
                        print(f"提取单条评论数据时出错: {str(e)}")
                        continue
                
                # 尝试点击下一页 - 使用更精确的选择器
                try:
                    # 滚动到分页区域
                    self.driver.execute_script("""
                        var pager = document.querySelector('.ui-page');
                        if(pager) pager.scrollIntoView({behavior: 'smooth', block: 'center'});
                    """)
                    time.sleep(2)
                    
                    # 使用更精确的选择器
                    next_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR, 
                            "div.ui-page a.ui-pager-next[href='#comment']"
                        ))
                    )
                    
                    # 检查是否是最后一页
                    if "disabled" in next_button.get_attribute("class"):
                        print("已到达最后一页")
                        break
                    
                    # 移除可能遮挡的元素
                    self.driver.execute_script("""
                        var elements = document.querySelectorAll('.J-global-toolbar, #InitCartUrl-mini');
                        elements.forEach(function(element) {
                            if(element) element.remove();
                        });
                    """)
                    
                    # 使用JavaScript模拟点击
                    self.driver.execute_script("""
                        var nextBtn = document.querySelector('div.ui-page a.ui-pager-next[href="#comment"]');
                        if(nextBtn) {
                            nextBtn.click();
                            console.log('下一页按钮已点击');
                        } else {
                            console.log('未找到下一页按钮');
                        }
                    """)
                    
                    # 等待页面加载和评论刷新
                    time.sleep(3)
                    
                    # 验证页面是否成功翻页
                    try:
                        WebDriverWait(self.driver, 5).until(
                            lambda driver: driver.execute_script(
                                "return document.querySelector('.ui-page').textContent.includes('下一页')"
                            )
                        )
                    except:
                        print("翻页可能未成功，重试中...")
                        continue
                    
                except Exception as e:
                    print(f"翻页失败: {str(e)}")
                    break
                    
            print(f"\n总共成功提取 {len(reviews_data)} 条评论")
                
        except Exception as e:
            print(f"获取评论出错: {str(e)}")
            
        return reviews_data

    def save_to_excel(self, data, filename='jd_reviews.csv'):
        """保存评论数据到CSV"""
        try:
            # 检查data/input目录是否存在，没有则创建
            input_dir = os.path.join('data', 'input')
            if not os.path.exists(input_dir):
                os.makedirs(input_dir)
            
            filepath = os.path.join(input_dir, filename)
            
            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"数据已保存到 {filepath}")
            print(f"成功保存 {len(data)} 条评论")
            
        except Exception as e:
            print(f"保存数据失败: {str(e)}")

    def run(self, product_url = "https://item.jd.com/100119535525.html#comment"):
        """运行爬虫主程序"""
        self.init_driver()
        try:
            self.login()
            print(f"开始爬取商品评论: {product_url}")
            reviews_data = self.get_reviews(product_url)
            if reviews_data:
                self.save_to_excel(reviews_data)
                print(f"共采集到 {len(reviews_data)} 条评论")
        except Exception as e:
            print(f"爬虫运行出错: {str(e)}")
        finally:
            time.sleep(2)
            self.driver.quit()

if __name__ == "__main__":
    spider = JDReviewSpider()
    # 让用户输入URL，如果直接回车则使用默认URL
    product_url = input("请输入需要爬的url(直接回车使用默认url):").strip()
    if not product_url:
        product_url = "https://item.jd.com/100119535525.html#comment"
    spider.run(product_url)




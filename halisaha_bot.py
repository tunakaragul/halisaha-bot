#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏟️ Halısaha Rezervasyon Bot - GitHub Actions
"""

import os
import sys
import time
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def parse_turkish_date(date_str):
    try:
        month_tr_to_num = {
            "Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4,
            "Mayıs": 5, "Haziran": 6, "Temmuz": 7, "Ağustos": 8,
            "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12
        }
        
        parts = date_str.strip().split()
        day = int(parts[0])
        month = month_tr_to_num[parts[1]]
        year = int(parts[2])
        
        return datetime(year, month, day)
    except:
        return None

def is_date_in_range(target_date_str, date_range_str):
    try:
        if target_date_str in date_range_str:
            return True
        
        if " - " not in date_range_str:
            return False
        
        range_parts = date_range_str.split(" - ")
        start_date_str = range_parts[0].strip()
        end_date_str = range_parts[1].strip()
        
        target_dt = parse_turkish_date(target_date_str)
        start_dt = parse_turkish_date(start_date_str)
        end_dt = parse_turkish_date(end_date_str)
        
        if target_dt and start_dt and end_dt:
            return start_dt <= target_dt <= end_dt
        
        return False
    except:
        return False

class HalisahaBot:
    def __init__(self):
        self.username = os.environ.get('HALISAHA_USERNAME')
        self.password = os.environ.get('HALISAHA_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError("Kullanıcı bilgileri eksik!")
        
        self.base_url = "https://spor.kadikoy.bel.tr"
        self.target_facility_url = "https://spor.kadikoy.bel.tr/spor-salonu/kalamis-spor?activityCategories=2"
        
        self.preferred_hours = [
            "20:00/21:00", "19:00/20:00", "21:00/22:00", 
            "22:00/23:00", "18:00/19:00"
        ]
        
        self.driver = None
    
    def send_email(self, subject, message):
        try:
            email = os.environ.get('NOTIFICATION_EMAIL')
            password = os.environ.get('EMAIL_PASSWORD')
            
            if not email or not password:
                logging.info("E-posta bilgileri yok, atlanıyor")
                return
            
            msg = MIMEMultipart()
            msg['From'] = email
            msg['To'] = email
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(email, password)
            server.send_message(msg)
            server.quit()
            
            logging.info(f"📧 E-posta gönderildi: {subject}")
        except Exception as e:
            logging.error(f"E-posta hatası: {str(e)}")
    
    def calculate_target_dates(self):
        today = datetime.now()
        target_dates = []
        
        for days_ahead in range(7, 21):
            target_date = today + timedelta(days=days_ahead)
            
            if target_date.weekday() == 0:  # Pazartesi
                target_dates.append({
                    'day_name': 'Pazartesi',
                    'turkish_date': self.format_turkish_date(target_date)
                })
            elif target_date.weekday() == 3:  # Perşembe
                target_dates.append({
                    'day_name': 'Perşembe',
                    'turkish_date': self.format_turkish_date(target_date)
                })
            
            if len(target_dates) >= 2:
                break
        
        return target_dates
    
    def format_turkish_date(self, date_obj):
        month_names = [
            "", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
        ]
        return f"{date_obj.day} {month_names[date_obj.month]} {date_obj.year}"
    
    def setup_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-images')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(20)
            return True
        except Exception as e:
            logging.error(f"Driver hatası: {str(e)}")
            return False
    
    def login(self):
        try:
            self.driver.get(f"{self.base_url}/giris")
            
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_field = self.driver.find_element(By.NAME, "password")
            
            username_field.send_keys(self.username)
            password_field.send_keys(self.password)
            
            login_button = self.driver.find_element(By.ID, "btnLoginSubmit")
            login_button.click()
            
            time.sleep(3)
            return "giris" not in self.driver.current_url
        except Exception as e:
            logging.error(f"Giriş hatası: {str(e)}")
            return False
    
    def reserve(self, target_date_str):
        try:
            self.driver.get(self.target_facility_url)
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "yonlendirme-info"))
            )
            
            # Tarih navigasyonu
            for attempt in range(5):
                current_date = self.driver.find_element(By.CLASS_NAME, "yonlendirme-info").text
                if is_date_in_range(target_date_str, current_date):
                    break
                
                button = self.driver.find_element(By.ID, "area-sonraki-hafta")
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('click'));", button)
                time.sleep(2)
            
            # Slot ara
            time.sleep(2)
            all_slots = self.driver.find_elements(By.CSS_SELECTOR, "div.lesson.active")
            
            for hour in self.preferred_hours:
                for slot in all_slots:
                    try:
                        date = slot.get_attribute("data-dateformatted")
                        slot_hour = slot.get_attribute("data-hour")
                        
                        if date == target_date_str and slot_hour == hour:
                            logging.info(f"🎯 Slot bulundu: {hour}")
                            
                            # Rezervasyon işlemi
                            self.driver.execute_script("arguments[0].click();", slot)
                            
                            popup = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "bootbox"))
                            )
                            
                            time.sleep(0.5)
                            rezerve_radio = popup.find_element(By.CSS_SELECTOR, "input[value='basvuru-yap']")
                            self.driver.execute_script("arguments[0].click();", rezerve_radio)
                            
                            devam_button = popup.find_element(By.CSS_SELECTOR, "button.btn.btn-blue.devam-et")
                            self.driver.execute_script("arguments[0].click();", devam_button)
                            
                            time.sleep(1)
                            rules_checkbox = self.driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                            self.driver.execute_script("arguments[0].click();", rules_checkbox)
                            
                            time.sleep(0.5)
                            self.driver.execute_script("""
                                var buttons = document.querySelectorAll('button.btn.btn-blue');
                                for(var i=0; i<buttons.length; i++) {
                                    if(buttons[i].textContent.trim() === 'Evet') {
                                        buttons[i].click();
                                        break;
                                    }
                                }
                            """)
                            
                            time.sleep(3)
                            return self.check_success(target_date_str, hour)
                    except:
                        continue
            
            return False
        except Exception as e:
            logging.error(f"Rezervasyon hatası: {str(e)}")
            return False
    
    def check_success(self, target_date, hour):
        try:
            self.driver.get(f"{self.base_url}/ClubMember/MyReservation.aspx")
            time.sleep(2)
            
            rows = self.driver.find_elements(By.CSS_SELECTOR, "#AreaReservationTable tbody tr")
            check_hour = hour.replace("/", " - ")
            
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 5:
                        hour_cell = cells[3].text
                        status = cells[4].text
                        
                        if check_hour in hour_cell and status == "Ön Onaylı":
                            return True
                except:
                    continue
            
            return False
        except:
            return False
    
    def run(self):
        try:
            logging.info("🚀 Halısaha Bot başladı")
            
            target_dates = self.calculate_target_dates()
            if not target_dates:
                logging.error("Hedef tarih bulunamadı")
                return
            
            if not self.setup_driver():
                return
            
            try:
                if not self.login():
                    logging.error("Giriş başarısız")
                    return
                
                success_count = 0
                for target in target_dates:
                    logging.info(f"Deneniyor: {target['day_name']} - {target['turkish_date']}")
                    
                    if self.reserve(target['turkish_date']):
                        success_count += 1
                        logging.info(f"✅ {target['day_name']} başarılı!")
                        
                        # Başarı e-postası
                        self.send_email(
                            f"🎉 {target['day_name']} Rezervasyonu Başarılı!",
                            f"Tarih: {target['turkish_date']}\nBot başarıyla çalıştı!"
                        )
                    else:
                        logging.info(f"❌ {target['day_name']} slot bulunamadı")
                
                # Özet e-posta
                self.send_email(
                    f"📊 Bot Raporu: {success_count}/{len(target_dates)} başarılı",
                    f"Çalışma zamanı: {datetime.now().strftime('%d.%m.%Y %H:%M')}\nBaşarılı rezervasyon: {success_count}"
                )
                
            finally:
                if self.driver:
                    try:
                        self.driver.save_screenshot("bot_result.png")
                    except:
                        pass
                    self.driver.quit()
                    
        except Exception as e:
            logging.error(f"Ana hata: {str(e)}")
            self.send_email("❌ Bot Hatası", f"Hata: {str(e)}")

def main():
    bot = HalisahaBot()
    bot.run()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏟️ Halısaha Rezervasyon Bot - Ayrı Günler
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
        self.target_day = os.environ.get('TARGET_DAY', 'PAZARTESI')  # PAZARTESI veya PERSEMBE
        
        if not self.username or not self.password:
            raise ValueError("Kullanıcı bilgileri eksik!")
        
        self.base_url = "https://spor.kadikoy.bel.tr"
        self.target_facility_url = "https://spor.kadikoy.bel.tr/spor-salonu/kalamis-spor?activityCategories=2"
        
        self.preferred_hours = [
            "20:00/21:00", "19:00/20:00", "21:00/22:00", 
            "22:00/23:00", "18:00/19:00"
        ]
        
        self.driver = None
        
        logging.info(f"🎯 Hedef gün: {self.target_day}")
    
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
    
    def calculate_target_date(self):
        """TARGET_DAY'e göre sadece bir tarih hesapla"""
        today = datetime.now()
        
        if self.target_day == "PAZARTESI":
            # Bir sonraki Pazartesi'yi bul
            days_ahead = 7 - today.weekday()  # Bu haftaki Pazartesi'ye kalan gün
            if today.weekday() == 6:  # Bugün Pazar ise
                days_ahead = 1  # Yarın Pazartesi
            else:
                days_ahead = 7 - today.weekday()  # Bir sonraki Pazartesi
            
            target_date = today + timedelta(days=days_ahead)
            
        elif self.target_day == "PERSEMBE":
            # Bir sonraki Perşembe'yi bul
            if today.weekday() == 2:  # Bugün Çarşamba ise
                days_ahead = 1  # Yarın Perşembe
            else:
                # Bir sonraki Perşembe'yi hesapla
                days_ahead = (3 - today.weekday()) % 7
                if days_ahead == 0:  # Bugün Perşembe ise
                    days_ahead = 7
            
            target_date = today + timedelta(days=days_ahead)
        
        else:
            logging.error(f"Geçersiz TARGET_DAY: {self.target_day}")
            return None
        
        return {
            'day_name': self.target_day.title(),
            'turkish_date': self.format_turkish_date(target_date)
        }
    
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
            logging.info(f"🚀 Halısaha Bot başladı - {self.target_day}")
            
            target = self.calculate_target_date()
            if not target:
                logging.error("Hedef tarih hesaplanamadı")
                return
            
            logging.info(f"🎯 Hedef: {target['day_name']} - {target['turkish_date']}")
            logging.info(f"⏰ Polling başlıyor: 25 dakika boyunca her 15 saniyede bir deneme")
            
            # POLLİNG SİSTEMİ
            max_duration_minutes = 25  # 25 dakika
            attempt_interval_seconds = 15  # 15 saniyede bir
            max_attempts = (max_duration_minutes * 60) // attempt_interval_seconds  # 100 deneme
            
            attempt_count = 0
            success = False
            start_time = datetime.now()
            
            while attempt_count < max_attempts and not success:
                attempt_count += 1
                current_time = datetime.now()
                
                logging.info(f"⚡ Deneme #{attempt_count}/{max_attempts} - {current_time.strftime('%H:%M:%S')}")
                
                if not self.setup_driver():
                    logging.error("Driver başlatılamadı, 15 saniye bekleyip tekrar deneniyor")
                    time.sleep(attempt_interval_seconds)
                    continue
                
                try:
                    if not self.login():
                        logging.error("Giriş başarısız, 15 saniye bekleyip tekrar deneniyor")
                        if self.driver:
                            self.driver.quit()
                        time.sleep(attempt_interval_seconds)
                        continue
                    
                    if self.reserve(target['turkish_date']):
                        success = True
                        elapsed_time = (datetime.now() - start_time).total_seconds()
                        
                        logging.info(f"🎉 BAŞARILI REZERVASYON!")
                        logging.info(f"📊 Deneme sayısı: {attempt_count}")
                        logging.info(f"⏱️ Toplam süre: {elapsed_time:.0f} saniye")
                        
                        # Başarı e-postası
                        self.send_email(
                            f"🎉 {target['day_name']} Rezervasyonu Başarılı!",
                            f"""🏟️ BAŞARILI REZERVASYON!
                            
    📅 Tarih: {target['turkish_date']}
    🔢 Deneme: #{attempt_count}/{max_attempts}
    ⏱️ Süre: {elapsed_time:.0f} saniye
    🕐 Başlangıç: {start_time.strftime('%H:%M:%S')}
    🕐 Bitiş: {current_time.strftime('%H:%M:%S')}
    
    Bot başarıyla çalıştı! 🚀"""
                        )
                        break
                    else:
                        logging.info(f"❌ Deneme #{attempt_count} - Slot henüz açılmamış")
                        
                except Exception as e:
                    logging.error(f"Deneme #{attempt_count} hatası: {str(e)}")
                    
                finally:
                    if self.driver:
                        try:
                            if success:
                                self.driver.save_screenshot(f"success_{attempt_count}.png")
                            else:
                                # Sadece her 10 denemede bir screenshot al (çok fazla olmasın)
                                if attempt_count % 10 == 0:
                                    self.driver.save_screenshot(f"attempt_{attempt_count}.png")
                        except:
                            pass
                        self.driver.quit()
                
                # Başarılı değilse bekle
                if not success and attempt_count < max_attempts:
                    logging.info(f"⏳ {attempt_interval_seconds} saniye bekleniyor...")
                    time.sleep(attempt_interval_seconds)
            
            # Polling sonu raporu
            total_time = (datetime.now() - start_time).total_seconds()
            
            if not success:
                logging.warning(f"⏰ Polling süresi doldu")
                logging.info(f"📊 Toplam deneme: {attempt_count}")
                logging.info(f"⏱️ Toplam süre: {total_time:.0f} saniye")
                
                # Başarısızlık e-postası
                self.send_email(
                    f"⏰ {target['day_name']} Polling Tamamlandı",
                    f"""⚠️ POLLING RAPORU
                    
    📅 Tarih: {target['turkish_date']}
    🔢 Toplam deneme: {attempt_count}
    ⏱️ Süre: {total_time:.0f} saniye ({max_duration_minutes} dakika)
    🕐 Başlangıç: {start_time.strftime('%H:%M:%S')}
    🕐 Bitiş: {datetime.now().strftime('%H:%M:%S')}
    
    Slot açılmadı veya çok hızlı kapandı. 😔"""
                )
            
        except Exception as e:
            logging.error(f"Ana hata: {str(e)}")
            self.send_email("❌ Bot Hatası", f"Hata: {str(e)}")

def main():
    bot = HalisahaBot()
    bot.run()

if __name__ == "__main__":
    main()

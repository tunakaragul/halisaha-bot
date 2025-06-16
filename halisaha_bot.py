#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏟️ Halısaha Rezervasyon Bot - PRE-CONNECTED ULTRA SPEED V2
"""

import os
import sys
import time
import smtplib
import logging
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

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

class PreConnectedBrowser:
    """Önceden bağlanmış browser yönetimi"""
    def __init__(self, browser_id, username, password, base_url, target_facility_url):
        self.browser_id = browser_id
        self.username = username
        self.password = password
        self.base_url = base_url
        self.target_facility_url = target_facility_url
        self.driver = None
        self.is_ready = False
        self.is_logged_in = False
        
    def setup_and_login(self):
        """Browser'ı kur ve login yap"""
        try:
            # Driver setup
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--window-size=1280,720')
            chrome_options.add_argument('--memory-pressure-off')
            chrome_options.add_argument('--max-connections-per-host=10')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(15)
            self.driver.implicitly_wait(2)
            
            logging.info(f"🔧 Browser #{self.browser_id} - Driver kuruldu")
            
            # Login işlemi
            self.driver.get(f"{self.base_url}/giris")
            
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_field = self.driver.find_element(By.NAME, "password")
            
            self.driver.execute_script(f"arguments[0].value = '{self.username}';", username_field)
            self.driver.execute_script(f"arguments[0].value = '{self.password}';", password_field)
            
            login_button = self.driver.find_element(By.ID, "btnLoginSubmit")
            self.driver.execute_script("arguments[0].click();", login_button)
            
            time.sleep(2)
            
            if "giris" not in self.driver.current_url:
                self.is_logged_in = True
                logging.info(f"✅ Browser #{self.browser_id} - Login başarılı")
                
                # Halısaha sayfasına git ve hazırla
                self.driver.get(self.target_facility_url)
                time.sleep(2)
                
                self.is_ready = True
                logging.info(f"🎯 Browser #{self.browser_id} - Hazır ve bekliyor!")
                return True
            else:
                logging.error(f"❌ Browser #{self.browser_id} - Login başarısız")
                return False
                
        except Exception as e:
            logging.error(f"❌ Browser #{self.browser_id} setup hatası: {str(e)}")
            return False
    
    def quick_reserve_attempt(self, target_date_str, preferred_hours):
        """Hızlı rezervasyon denemesi"""
        if not self.is_ready:
            return False
            
        try:
            # Sayfa yenile ve slot kontrol
            self.driver.refresh()
            time.sleep(1)
            
            # Tarih navigasyonu
            for attempt in range(3):
                try:
                    current_date = self.driver.find_element(By.CLASS_NAME, "yonlendirme-info").text
                    if is_date_in_range(target_date_str, current_date):
                        break
                    
                    button = self.driver.find_element(By.ID, "area-sonraki-hafta")
                    self.driver.execute_script("arguments[0].click();", button)
                    time.sleep(0.5)
                except:
                    break
            
            # Slot arama
            all_slots = self.driver.find_elements(By.CSS_SELECTOR, "div.lesson.active")
            logging.info(f"🔍 Browser #{self.browser_id} - {len(all_slots)} slot bulundu")
            
            for hour in preferred_hours:
                for slot in all_slots:
                    try:
                        date = slot.get_attribute("data-dateformatted")
                        slot_hour = slot.get_attribute("data-hour")
                        
                        if date == target_date_str and slot_hour == hour:
                            logging.info(f"🎯 Browser #{self.browser_id} - SLOT BULUNDU: {hour}")
                            
                            # LIGHTNING rezervasyon
                            self.driver.execute_script("arguments[0].click();", slot)
                            
                            popup = WebDriverWait(self.driver, 3).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "bootbox"))
                            )
                            
                            rezerve_radio = popup.find_element(By.CSS_SELECTOR, "input[value='basvuru-yap']")
                            self.driver.execute_script("arguments[0].click();", rezerve_radio)
                            
                            devam_button = popup.find_element(By.CSS_SELECTOR, "button.btn.btn-blue.devam-et")
                            self.driver.execute_script("arguments[0].click();", devam_button)
                            
                            time.sleep(0.2)
                            rules_checkbox = self.driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                            self.driver.execute_script("arguments[0].click();", rules_checkbox)
                            
                            self.driver.execute_script("""
                                var buttons = document.querySelectorAll('button.btn.btn-blue');
                                for(var i=0; i<buttons.length; i++) {
                                    if(buttons[i].textContent.trim() === 'Evet') {
                                        buttons[i].click();
                                        return true;
                                    }
                                }
                            """)
                            
                            time.sleep(1)
                            return self.check_success(target_date_str, hour)
                            
                    except Exception as e:
                        continue
            
            return False
            
        except Exception as e:
            logging.error(f"Browser #{self.browser_id} rezervasyon hatası: {str(e)}")
            return False
    
    def check_success(self, target_date, hour):
        """Başarı kontrolü"""
        try:
            self.driver.get(f"{self.base_url}/ClubMember/MyReservation.aspx")
            time.sleep(1)
            
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
    
    def cleanup(self):
        """Browser'ı temizle"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

class HalisahaBot:
    def __init__(self):
        self.username = os.environ.get('HALISAHA_USERNAME')
        self.password = os.environ.get('HALISAHA_PASSWORD')
        self.target_day = os.environ.get('TARGET_DAY', 'PAZARTESI')
        
        if not self.username or not self.password:
            raise ValueError("Kullanıcı bilgileri eksik!")
        
        self.base_url = "https://spor.kadikoy.bel.tr"
        self.target_facility_url = "https://spor.kadikoy.bel.tr/spor-salonu/kalamis-spor?activityCategories=2"
        
        self.preferred_hours = [
            "20:00/21:00", "19:00/20:00", "21:00/22:00", 
            "22:00/23:00", "18:00/19:00"
        ]
        
        self.browser_pool = []
        
        logging.info(f"🎯 PRE-CONNECTED Bot - Hedef gün: {self.target_day}")
    
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
        """TARGET_DAY'e göre 1 hafta sonraki tarihi hesapla"""
        today = datetime.now()
        
        day_map = {
            "PAZARTESI": 0, "SALI": 1, "CARSAMBA": 2, "PERSEMBE": 3
        }
        
        if self.target_day not in day_map:
            logging.error(f"Geçersiz TARGET_DAY: {self.target_day}")
            return None
        
        target_weekday = day_map[self.target_day]
        current_weekday = today.weekday()
        
        # 1 hafta sonraki hedef günü hesapla
        if current_weekday == (target_weekday - 1) % 7:  # Bir gün önce
            days_ahead = 8  # 1 hafta sonraki
        else:
            days_to_target = (target_weekday - current_weekday) % 7
            if days_to_target == 0:
                days_to_target = 7
            days_ahead = days_to_target + 7  # 1 hafta sonraki
        
        target_date = today + timedelta(days=days_ahead)
        
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
    
    def setup_browser_pool(self):
        """23:54'te browser pool'u hazırla"""
        logging.info("🏗️ Browser Pool kuruluyor (4 browser)...")
        
        max_browsers = 4
        
        def setup_single_browser(browser_id):
            browser = PreConnectedBrowser(
                browser_id, self.username, self.password, 
                self.base_url, self.target_facility_url
            )
            
            if browser.setup_and_login():
                return browser
            else:
                browser.cleanup()
                return None
        
        # Paralel browser kurulumu
        with ThreadPoolExecutor(max_workers=max_browsers) as executor:
            futures = [
                executor.submit(setup_single_browser, i+1) 
                for i in range(max_browsers)
            ]
            
            for future in as_completed(futures):
                try:
                    browser = future.result()
                    if browser and browser.is_ready:
                        self.browser_pool.append(browser)
                except Exception as e:
                    logging.error(f"Browser setup hatası: {str(e)}")
        
        ready_count = len(self.browser_pool)
        logging.info(f"🎯 Browser Pool hazır: {ready_count}/4 browser aktif")
        
        return ready_count > 0
    
    def run_pre_connected_attack(self, target_date_str):
        """Hazır browser'larla saldırı"""
        if not self.browser_pool:
            logging.error("❌ Hiç hazır browser yok!")
            return False
        
        logging.info(f"🚀 PRE-CONNECTED ATTACK başladı! {len(self.browser_pool)} browser hazır")
        
        def single_browser_attack(browser):
            return browser.quick_reserve_attempt(target_date_str, self.preferred_hours)
        
        # Tüm browser'ları paralel çalıştır
        with ThreadPoolExecutor(max_workers=len(self.browser_pool)) as executor:
            futures = [
                executor.submit(single_browser_attack, browser) 
                for browser in self.browser_pool
            ]
            
            for future in as_completed(futures):
                try:
                    if future.result():
                        logging.info("🏆 PRE-CONNECTED ATTACK BAŞARILI!")
                        
                        # Diğer browser'ları durdur
                        for f in futures:
                            f.cancel()
                        
                        return True
                except Exception as e:
                    logging.error(f"Browser attack hatası: {str(e)}")
        
        return False
    
    def cleanup_browser_pool(self):
        """Tüm browser'ları temizle"""
        for browser in self.browser_pool:
            browser.cleanup()
        self.browser_pool.clear()
        logging.info("🧹 Browser Pool temizlendi")
    
    def run_pre_connected_ultra_speed(self):
        try:
            logging.info(f"🚀 PRE-CONNECTED ULTRA SPEED Bot başladı - {self.target_day}")
            
            target = self.calculate_target_date()
            if not target:
                logging.error("Hedef tarih hesaplanamadı")
                return
            
            logging.info(f"🎯 Hedef: {target['day_name']} - {target['turkish_date']}")
            logging.info(f"📋 Strateji: 23:54 Browser Pool → 23:57 Attack → 00:03 Finish")
            
            start_time = datetime.now()
            
            # PHASE 1: 23:54'te Browser Pool Kur
            logging.info("⏰ Phase 1: Browser Pool kuruluyor...")
            if not self.setup_browser_pool():
                logging.error("❌ Browser Pool kurulamadı!")
                self.send_email("❌ Browser Pool Hatası", "Hiç browser kurulmadı!")
                return
            
            logging.info("✅ Phase 1 tamamlandı - Browser'lar hazır!")
            
            # PHASE 2: 23:57-00:03 Attack Window
            logging.info("⏰ Phase 2: Attack window başladı!")
            
            attack_duration = 6 * 60  # 6 dakika (23:57-00:03)
            attack_interval = 3  # 3 saniyede bir
            max_attacks = attack_duration // attack_interval
            
            attack_count = 0
            success = False
            
            while attack_count < max_attacks and not success:
                attack_count += 1
                current_time = datetime.now()
                
                logging.info(f"⚡ Attack #{attack_count}/{max_attacks} - {current_time.strftime('%H:%M:%S')}")
                
                # Her 10 attackte bir browser health check
                if attack_count % 10 == 0:
                    alive_browsers = [b for b in self.browser_pool if b.is_ready]
                    logging.info(f"💖 Health Check: {len(alive_browsers)}/{len(self.browser_pool)} browser aktif")
                
                # Attack!
                if self.run_pre_connected_attack(target['turkish_date']):
                    success = True
                    elapsed_time = (datetime.now() - start_time).total_seconds()
                    
                    logging.info(f"🏆 PRE-CONNECTED BAŞARILI REZERVASYON!")
                    logging.info(f"📊 Attack sayısı: {attack_count}")
                    logging.info(f"⏱️ Toplam süre: {elapsed_time:.0f} saniye")
                    
                    self.send_email(
                        f"🏆 PRE-CONNECTED {target['day_name']} BAŞARILI!",
                        f"""🚀 PRE-CONNECTED ULTRA SPEED BAŞARILI!
                        
📅 Tarih: {target['turkish_date']}
🔢 Attack: #{attack_count}/{max_attacks}
⏱️ Süre: {elapsed_time:.0f} saniye
🕐 Başlangıç: {start_time.strftime('%H:%M:%S')}
🕐 Bitiş: {current_time.strftime('%H:%M:%S')}
🏗️ Browser Pool: {len(self.browser_pool)} browser
🚀 Pre-connected strateji mükemmel çalıştı!

YENİ STRATEJİ BAŞARILI! 🏆"""
                    )
                    break
                else:
                    logging.info(f"❌ Attack #{attack_count} - Slot henüz yok")
                
                # Kısa bekleme
                if attack_count < max_attacks:
                    time.sleep(attack_interval)
            
            # Final rapor
            total_time = (datetime.now() - start_time).total_seconds()
            
            if not success:
                logging.warning(f"⏰ Attack window sona erdi")
                logging.info(f"📊 Toplam attack: {attack_count}")
                logging.info(f"⏱️ Toplam süre: {total_time:.0f} saniye")
                
                self.send_email(
                    f"⏰ PRE-CONNECTED {target['day_name']} Tamamlandı",
                    f"""⚠️ PRE-CONNECTED ATTACK RAPORU
                    
📅 Tarih: {target['turkish_date']}
🔢 Toplam attack: {attack_count}
⏱️ Süre: {total_time:.0f} saniye (6 dakika window)
🕐 Başlangıç: {start_time.strftime('%H:%M:%S')}
🕐 Bitiş: {datetime.now().strftime('%H:%M:%S')}
🏗️ Browser Pool: {len(self.browser_pool)} browser hazırdı

Pre-connected strateji çalıştı ama slot alınamadı. 
Browser'lar hazırdı, rekabet çok yoğun! 😔"""
                )
            
        except Exception as e:
            logging.error(f"PRE-CONNECTED Ana hata: {str(e)}")
            self.send_email("❌ PRE-CONNECTED Bot Hatası", f"Hata: {str(e)}")
        
        finally:
            # Browser'ları temizle
            self.cleanup_browser_pool()

def main():
    bot = HalisahaBot()
    bot.run_pre_connected_ultra_speed()

if __name__ == "__main__":
    main()

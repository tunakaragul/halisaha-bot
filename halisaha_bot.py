#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏟️ Halısaha Rezervasyon Bot - ULTRA SPEED VERSION
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

class HalisahaBot:
    def __init__(self, browser_id=1):
        self.username = os.environ.get('HALISAHA_USERNAME')
        self.password = os.environ.get('HALISAHA_PASSWORD')
        self.target_day = os.environ.get('TARGET_DAY', 'PAZARTESI')  # PAZARTESI veya PERSEMBE
        self.browser_id = browser_id
        
        if not self.username or not self.password:
            raise ValueError("Kullanıcı bilgileri eksik!")
        
        self.base_url = "https://spor.kadikoy.bel.tr"
        self.target_facility_url = "https://spor.kadikoy.bel.tr/spor-salonu/kalamis-spor?activityCategories=2"
        
        # Saat öncelik sırası
        self.preferred_hours = [
            "20:00/21:00", "19:00/20:00", "21:00/22:00", 
            "22:00/23:00", "18:00/19:00"
        ]
        
        self.driver = None
        
        logging.info(f"🎯 Browser #{self.browser_id} - Hedef gün: {self.target_day}")
    
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
        
        if self.target_day == "PAZARTESI":
            if today.weekday() == 6:  # Pazar
                days_ahead = 8  # 1 hafta sonraki Pazartesi
            else:
                days_to_next_monday = (7 - today.weekday()) % 7
                if days_to_next_monday == 0:
                    days_to_next_monday = 7
                days_ahead = days_to_next_monday + 7
            
            target_date = today + timedelta(days=days_ahead)
            
        elif self.target_day == "PERSEMBE":
            if today.weekday() == 2:  # Çarşamba
                days_ahead = 8  # 1 hafta sonraki Perşembe
            else:
                days_to_next_thursday = (3 - today.weekday()) % 7
                if days_to_next_thursday == 0:
                    days_to_next_thursday = 7
                days_ahead = days_to_next_thursday + 7
            
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
    
    def setup_driver_ultra_fast(self):
        """Süper hızlı driver setup"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--disable-javascript')  # Sayfayı hızlandır
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-background-networking')
            chrome_options.add_argument('--disable-sync')
            chrome_options.add_argument('--disable-translate')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--window-size=1280,720')  # Küçük pencere
            chrome_options.add_argument('--aggressive-cache-discard')
            chrome_options.add_argument('--memory-pressure-off')
            
            # Ağ hızlandırma
            chrome_options.add_argument('--enable-tcp-fast-open')
            chrome_options.add_argument('--max-connections-per-host=10')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(10)  # 20→10 saniye
            
            # İmplicit wait'i azalt
            self.driver.implicitly_wait(1)
            
            return True
        except Exception as e:
            logging.error(f"Browser #{self.browser_id} Driver hatası: {str(e)}")
            return False
    
    def login_ultra_fast(self):
        """Hızlı giriş"""
        try:
            self.driver.get(f"{self.base_url}/giris")
            
            # Hızlı element bulma
            username_field = WebDriverWait(self.driver, 5).until(  # 10→5
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_field = self.driver.find_element(By.NAME, "password")
            
            # JavaScript ile hızlı yazma
            self.driver.execute_script(f"arguments[0].value = '{self.username}';", username_field)
            self.driver.execute_script(f"arguments[0].value = '{self.password}';", password_field)
            
            login_button = self.driver.find_element(By.ID, "btnLoginSubmit")
            self.driver.execute_script("arguments[0].click();", login_button)
            
            time.sleep(1)  # 3→1 saniye
            return "giris" not in self.driver.current_url
        except Exception as e:
            logging.error(f"Browser #{self.browser_id} Giriş hatası: {str(e)}")
            return False
    
    def reserve_lightning_speed(self, target_date_str):
        """Şimşek hızında rezervasyon"""
        try:
            self.driver.get(self.target_facility_url)
            
            # Hızlı sayfa yüklenme bekleme
            WebDriverWait(self.driver, 5).until(  # 10→5
                EC.presence_of_element_located((By.CLASS_NAME, "yonlendirme-info"))
            )
            
            # Tarih navigasyonu - hızlandırılmış
            for attempt in range(3):  # 5→3
                current_date = self.driver.find_element(By.CLASS_NAME, "yonlendirme-info").text
                if is_date_in_range(target_date_str, current_date):
                    break
                
                button = self.driver.find_element(By.ID, "area-sonraki-hafta")
                self.driver.execute_script("arguments[0].click();", button)  # Event dispatch yerine direkt click
                time.sleep(0.5)  # 2→0.5 saniye
            
            # Slot arama - minimal wait
            time.sleep(0.5)  # 2→0.5 saniye
            all_slots = self.driver.find_elements(By.CSS_SELECTOR, "div.lesson.active")
            
            logging.info(f"🔍 Browser #{self.browser_id} - {len(all_slots)} aktif slot bulundu")
            
            # Tüm saatleri paralel dene
            for hour in self.preferred_hours:
                for slot in all_slots:
                    try:
                        date = slot.get_attribute("data-dateformatted")
                        slot_hour = slot.get_attribute("data-hour")
                        
                        if date == target_date_str and slot_hour == hour:
                            logging.info(f"🎯 Browser #{self.browser_id} - Slot bulundu: {hour}")
                            
                            # ULTRA HIZLI rezervasyon işlemi
                            self.driver.execute_script("arguments[0].click();", slot)
                            
                            # Popup bekle - kısa timeout
                            popup = WebDriverWait(self.driver, 3).until(  # 5→3
                                EC.presence_of_element_located((By.CLASS_NAME, "bootbox"))
                            )
                            
                            # Ardarda tüm işlemler - NO SLEEP!
                            rezerve_radio = popup.find_element(By.CSS_SELECTOR, "input[value='basvuru-yap']")
                            self.driver.execute_script("arguments[0].click();", rezerve_radio)
                            
                            devam_button = popup.find_element(By.CSS_SELECTOR, "button.btn.btn-blue.devam-et")
                            self.driver.execute_script("arguments[0].click();", devam_button)
                            
                            # Mikro wait - rules checkbox için
                            time.sleep(0.2)  # 1→0.2 saniye
                            rules_checkbox = self.driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                            self.driver.execute_script("arguments[0].click();", rules_checkbox)
                            
                            # Final click - NO WAIT!
                            self.driver.execute_script("""
                                var buttons = document.querySelectorAll('button.btn.btn-blue');
                                for(var i=0; i<buttons.length; i++) {
                                    if(buttons[i].textContent.trim() === 'Evet') {
                                        buttons[i].click();
                                        return true;
                                    }
                                }
                            """)
                            
                            time.sleep(1)  # 3→1 saniye - success check için
                            success_result = self.check_success_fast(target_date_str, hour)
                            
                            if success_result:
                                logging.info(f"🏆 Browser #{self.browser_id} - REZERVASYON BAŞARILI!")
                                return True
                            else:
                                logging.info(f"⚡ Browser #{self.browser_id} - Devam ediyor...")
                                
                    except Exception as e:
                        # Hata olursa devam et
                        continue
            
            return False
        except Exception as e:
            logging.error(f"Browser #{self.browser_id} Rezervasyon hatası: {str(e)}")
            return False
    
    def check_success_fast(self, target_date, hour):
        """Hızlı başarı kontrolü"""
        try:
            self.driver.get(f"{self.base_url}/ClubMember/MyReservation.aspx")
            time.sleep(1)  # 2→1 saniye
            
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
    
    def single_browser_attempt(self, target_date_str, browser_id):
        """Tek browser denemesi"""
        bot = HalisahaBot(browser_id)
        
        try:
            if not bot.setup_driver_ultra_fast():
                return False
            
            if not bot.login_ultra_fast():
                return False
            
            return bot.reserve_lightning_speed(target_date_str)
            
        except Exception as e:
            logging.error(f"Browser #{browser_id} genel hatası: {str(e)}")
            return False
        finally:
            if bot.driver:
                try:
                    bot.driver.quit()
                except:
                    pass
    
    def multi_browser_attack(self, target_date_str):
        """🚀 ÇOKLU BROWSER SALDIRISI"""
        logging.info("🚀 ÇOKLU BROWSER ATTACK BAŞLADI!")
        
        max_browsers = 4  # Aynı anda 4 browser
        success = False
        
        with ThreadPoolExecutor(max_workers=max_browsers) as executor:
            # Tüm browser'ları aynı anda başlat
            futures = [
                executor.submit(self.single_browser_attempt, target_date_str, i+1) 
                for i in range(max_browsers)
            ]
            
            # İlk başarılı olanı bekle
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        success = True
                        logging.info("🏆 ÇOKLU BROWSER'DAN BİRİ BAŞARILI!")
                        
                        # Diğer browser'ları durdur
                        for f in futures:
                            f.cancel()
                        
                        break
                except Exception as e:
                    logging.error(f"Browser future hatası: {str(e)}")
        
        return success
    
    def run_ultra_speed(self):
        try:
            logging.info(f"🚀 ULTRA SPEED Halısaha Bot başladı - {self.target_day}")
            
            target = self.calculate_target_date()
            if not target:
                logging.error("Hedef tarih hesaplanamadı")
                return
            
            logging.info(f"🎯 Hedef: {target['day_name']} - {target['turkish_date']}")
            logging.info(f"⏰ ULTRA SPEED Polling: 23:55'ten itibaren 15 dakika boyunca her 5 saniyede")
            
            # YENİ POLLİNG SİSTEMİ
            max_duration_minutes = 15  # 25→15 dakika (23:55-00:10 arası yeterli)
            attempt_interval_seconds = 5   # 15→5 saniyede bir
            max_attempts = (max_duration_minutes * 60) // attempt_interval_seconds  # 180 deneme
            
            attempt_count = 0
            success = False
            start_time = datetime.now()
            
            # İlk 00:00'a kadar normal polling, sonra çoklu browser
            while attempt_count < max_attempts and not success:
                attempt_count += 1
                current_time = datetime.now()
                
                logging.info(f"⚡ Deneme #{attempt_count}/{max_attempts} - {current_time.strftime('%H:%M:%S')}")
                
                # Saat 00:00'a yaklaştığında çoklu browser kullan
                if current_time.strftime('%H:%M') >= '23:59':
                    logging.info("🚨 ÇOKLU BROWSER MODU AKTİF!")
                    
                    if self.multi_browser_attack(target['turkish_date']):
                        success = True
                        elapsed_time = (datetime.now() - start_time).total_seconds()
                        
                        logging.info(f"🎉 ULTRA SPEED BAŞARILI REZERVASYON!")
                        logging.info(f"📊 Deneme sayısı: {attempt_count}")
                        logging.info(f"⏱️ Toplam süre: {elapsed_time:.0f} saniye")
                        
                        # Başarı e-postası
                        self.send_email(
                            f"🏆 ULTRA SPEED {target['day_name']} Rezervasyonu BAŞARILI!",
                            f"""🚀 ULTRA SPEED BAŞARILI REZERVASYON!
                            
    📅 Tarih: {target['turkish_date']}
    🔢 Deneme: #{attempt_count}/{max_attempts}
    ⏱️ Süre: {elapsed_time:.0f} saniye
    🕐 Başlangıç: {start_time.strftime('%H:%M:%S')}
    🕐 Bitiş: {current_time.strftime('%H:%M:%S')}
    🚀 Çoklu browser saldırısı başarılı!
    
    ULTRA SPEED Bot mükemmel çalıştı! 🏆"""
                        )
                        break
                else:
                    # Normal single browser polling
                    if not self.setup_driver_ultra_fast():
                        logging.error("Driver başlatılamadı, 5 saniye bekleyip tekrar deneniyor")
                        time.sleep(attempt_interval_seconds)
                        continue
                    
                    try:
                        if not self.login_ultra_fast():
                            logging.error("Giriş başarısız, 5 saniye bekleyip tekrar deneniyor")
                            if self.driver:
                                self.driver.quit()
                            time.sleep(attempt_interval_seconds)
                            continue
                        
                        if self.reserve_lightning_speed(target['turkish_date']):
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
        
        ULTRA SPEED Bot başarıyla çalıştı! 🚀"""
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
                                    self.driver.save_screenshot(f"ultra_success_{attempt_count}.png")
                                elif attempt_count % 20 == 0:  # 10→20 (daha az screenshot)
                                    self.driver.save_screenshot(f"ultra_attempt_{attempt_count}.png")
                            except:
                                pass
                            self.driver.quit()
                
                # Başarılı değilse kısa bekle
                if not success and attempt_count < max_attempts:
                    logging.info(f"⏳ {attempt_interval_seconds} saniye bekleniyor...")
                    time.sleep(attempt_interval_seconds)
            
            # Polling sonu raporu
            total_time = (datetime.now() - start_time).total_seconds()
            
            if not success:
                logging.warning(f"⏰ ULTRA SPEED Polling süresi doldu")
                logging.info(f"📊 Toplam deneme: {attempt_count}")
                logging.info(f"⏱️ Toplam süre: {total_time:.0f} saniye")
                
                # Başarısızlık e-postası
                self.send_email(
                    f"⏰ ULTRA SPEED {target['day_name']} Polling Tamamlandı",
                    f"""⚠️ ULTRA SPEED POLLING RAPORU
                    
    📅 Tarih: {target['turkish_date']}
    🔢 Toplam deneme: {attempt_count}
    ⏱️ Süre: {total_time:.0f} saniye ({max_duration_minutes} dakika)
    🕐 Başlangıç: {start_time.strftime('%H:%M:%S')}
    🕐 Bitiş: {datetime.now().strftime('%H:%M:%S')}
    
    Çoklu browser saldırısına rağmen slot alınamadı. Rekabet çok yoğun! 😔"""
                )
            
        except Exception as e:
            logging.error(f"ULTRA SPEED Ana hata: {str(e)}")
            self.send_email("❌ ULTRA SPEED Bot Hatası", f"Hata: {str(e)}")

def main():
    bot = HalisahaBot()
    bot.run_ultra_speed()

if __name__ == "__main__":
    main()

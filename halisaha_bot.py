#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏟️ Halısaha Rezervasyon Bot - ULTIMATE DEBUG VERSION
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
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def parse_turkish_date(date_str):
    try:
        month_tr_to_num = {
            "Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4,
            "Mayıs": 5, "Haziran": 6, "Temmuz": 7, "Ağustos": 8,
            "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12,
            "Haz": 6, "Tem": 7, "Ağu": 8, "Eyl": 9, "Eki": 10, "Kas": 11, "Ara": 12  # Kısa format
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

class UltimateDebugBrowser:
    """ULTIMATE Debug browser"""
    def __init__(self, browser_id, username, password, base_url, target_facility_url):
        self.browser_id = browser_id
        self.username = username
        self.password = password
        self.base_url = base_url
        self.target_facility_url = target_facility_url
        self.driver = None
        self.is_ready = False
        
    def quick_setup_and_login(self, max_time=45):
        """Hızlı setup + timeout protection"""
        start_time = time.time()
        
        try:
            logging.info(f"🔧 Browser #{self.browser_id} - Setup başladı")
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--window-size=800,600')
            chrome_options.add_argument('--memory-pressure-off')
            # Alert handling
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-notifications')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(8)
            self.driver.implicitly_wait(1)
            
            elapsed = time.time() - start_time
            if elapsed > max_time:
                return False
            
            # Login
            self.driver.get(f"{self.base_url}/giris")
            
            username_field = WebDriverWait(self.driver, 4).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_field = self.driver.find_element(By.NAME, "password")
            
            self.driver.execute_script(f"arguments[0].value = '{self.username}';", username_field)
            self.driver.execute_script(f"arguments[0].value = '{self.password}';", password_field)
            
            login_button = self.driver.find_element(By.ID, "btnLoginSubmit")
            self.driver.execute_script("arguments[0].click();", login_button)
            
            time.sleep(1)
            
            elapsed = time.time() - start_time
            if elapsed > max_time:
                return False
            
            if "giris" not in self.driver.current_url:
                self.driver.get(self.target_facility_url)
                time.sleep(1)
                
                self.is_ready = True
                elapsed = time.time() - start_time
                logging.info(f"✅ Browser #{self.browser_id} - HAZIR! ({elapsed:.1f}s)")
                return True
            else:
                logging.error(f"❌ Browser #{self.browser_id} - Login başarısız")
                return False
                
        except Exception as e:
            elapsed = time.time() - start_time
            logging.error(f"❌ Browser #{self.browser_id} - Hata ({elapsed:.1f}s): {str(e)}")
            return False
    
    def ultimate_debug_attempt(self, target_date_str, preferred_hours):
        """ULTIMATE Debug + Reserve"""
        if not self.is_ready:
            return False
            
        try:
            # Alert handling
            try:
                alert = self.driver.switch_to.alert
                alert.dismiss()
                logging.info(f"🚨 Browser #{self.browser_id} - Alert kapatıldı")
            except:
                pass
            
            # Sayfa refresh
            self.driver.refresh()
            time.sleep(0.5)
            
            # PHASE 1: TARİH DEBUG
            logging.info(f"🗓️ Browser #{self.browser_id} - TARİH DEBUG BAŞLADI")
            
            try:
                current_date_element = self.driver.find_element(By.CLASS_NAME, "yonlendirme-info")
                current_date = current_date_element.text
                logging.info(f"📅 Browser #{self.browser_id} - Mevcut sayfa tarihi: '{current_date}'")
                logging.info(f"🎯 Browser #{self.browser_id} - Hedef tarih: '{target_date_str}'")
                logging.info(f"🔍 Browser #{self.browser_id} - Tarih eşleşiyor mu: {is_date_in_range(target_date_str, current_date)}")
            except Exception as e:
                logging.error(f"❌ Browser #{self.browser_id} - Tarih element bulunamadı: {str(e)}")
            
            # Tarih navigasyonu
            for attempt in range(2):
                try:
                    current_date = self.driver.find_element(By.CLASS_NAME, "yonlendirme-info").text
                    
                    if is_date_in_range(target_date_str, current_date):
                        logging.info(f"✅ Browser #{self.browser_id} - Tarih eşleşti! (Deneme #{attempt+1})")
                        break
                    
                    logging.info(f"➡️ Browser #{self.browser_id} - Sonraki hafta tıklanıyor (Deneme #{attempt+1})")
                    button = self.driver.find_element(By.ID, "area-sonraki-hafta")
                    self.driver.execute_script("arguments[0].click();", button)
                    time.sleep(0.3)
                    
                    # Yeni tarih kontrolü
                    new_date = self.driver.find_element(By.CLASS_NAME, "yonlendirme-info").text
                    logging.info(f"📅 Browser #{self.browser_id} - Yeni tarih: '{new_date}'")
                    
                except Exception as e:
                    logging.error(f"❌ Browser #{self.browser_id} - Tarih nav hatası (Deneme #{attempt+1}): {str(e)}")
                    break
            
            # PHASE 2: SLOT DEBUG
            logging.info(f"🔍 Browser #{self.browser_id} - SLOT DEBUG BAŞLADI")
            
            all_slots = self.driver.find_elements(By.CSS_SELECTOR, "div.lesson.active")
            logging.info(f"📊 Browser #{self.browser_id} - Toplam {len(all_slots)} aktif slot bulundu")
            
            # İlk 5 slotu detaylı debug
            if len(all_slots) > 0:
                logging.info(f"🔬 Browser #{self.browser_id} - İLK 5 SLOT DEBUG:")
                for i, slot in enumerate(all_slots[:5]):
                    try:
                        date = slot.get_attribute("data-dateformatted")
                        slot_hour = slot.get_attribute("data-hour")
                        slot_text = slot.text.strip()
                        slot_class = slot.get_attribute("class")
                        
                        logging.info(f"    📍 Slot {i+1}:")
                        logging.info(f"        Tarih: '{date}'")
                        logging.info(f"        Saat: '{slot_hour}'")
                        logging.info(f"        Text: '{slot_text}'")
                        logging.info(f"        Class: '{slot_class}'")
                        
                        # Tarih eşleşme kontrolü
                        date_match = (date == target_date_str)
                        logging.info(f"        Tarih eşleşiyor: {date_match}")
                        
                        # Saat eşleşme kontrolü
                        hour_match = slot_hour in preferred_hours
                        logging.info(f"        Saat eşleşiyor: {hour_match} (Aranan: {preferred_hours})")
                        
                    except Exception as e:
                        logging.error(f"        ❌ Slot {i+1} debug hatası: {str(e)}")
            
            # PHASE 3: HEDEF SLOT ARAMA
            logging.info(f"🎯 Browser #{self.browser_id} - HEDEF SLOT ARAMA")
            logging.info(f"🎯 Browser #{self.browser_id} - Hedef tarih: '{target_date_str}'")
            logging.info(f"🎯 Browser #{self.browser_id} - Hedef saatler: {preferred_hours}")
            
            found_any_target = False
            
            for hour in preferred_hours:
                logging.info(f"🕐 Browser #{self.browser_id} - '{hour}' saati aranıyor...")
                
                for i, slot in enumerate(all_slots):
                    try:
                        date = slot.get_attribute("data-dateformatted")
                        slot_hour = slot.get_attribute("data-hour")
                        
                        if date == target_date_str and slot_hour == hour:
                            found_any_target = True
                            logging.info(f"🎯 Browser #{self.browser_id} - HEDEF SLOT BULUNDU!")
                            logging.info(f"    Slot #{i+1}: Tarih='{date}' Saat='{slot_hour}'")
                            
                            # Reserve attempt
                            logging.info(f"💥 Browser #{self.browser_id} - Rezervasyon denemesi başladı...")
                            
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", slot)
                            time.sleep(0.1)
                            self.driver.execute_script("arguments[0].click();", slot)
                            
                            # Popup wait
                            try:
                                popup = WebDriverWait(self.driver, 3).until(
                                    EC.presence_of_element_located((By.CLASS_NAME, "bootbox"))
                                )
                                logging.info(f"✅ Browser #{self.browser_id} - Popup açıldı")
                                
                                rezerve_radio = popup.find_element(By.CSS_SELECTOR, "input[value='basvuru-yap']")
                                self.driver.execute_script("arguments[0].click();", rezerve_radio)
                                logging.info(f"✅ Browser #{self.browser_id} - Rezerve radio seçildi")
                                
                                devam_button = popup.find_element(By.CSS_SELECTOR, "button.btn.btn-blue.devam-et")
                                self.driver.execute_script("arguments[0].click();", devam_button)
                                logging.info(f"✅ Browser #{self.browser_id} - Devam butonu tıklandı")
                                
                                time.sleep(0.2)
                                rules_checkbox = self.driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                                self.driver.execute_script("arguments[0].click();", rules_checkbox)
                                logging.info(f"✅ Browser #{self.browser_id} - Rules checkbox işaretlendi")
                                
                                self.driver.execute_script("""
                                    var buttons = document.querySelectorAll('button.btn.btn-blue');
                                    for(var i=0; i<buttons.length; i++) {
                                        if(buttons[i].textContent.trim() === 'Evet') {
                                            buttons[i].click();
                                            return true;
                                        }
                                    }
                                """)
                                logging.info(f"✅ Browser #{self.browser_id} - Final 'Evet' butonu tıklandı")
                                
                                time.sleep(0.5)
                                success = self.quick_success_check(target_date_str, hour)
                                
                                if success:
                                    logging.info(f"🏆 Browser #{self.browser_id} - REZERVASYON BAŞARILI!")
                                    return True
                                else:
                                    logging.info(f"❌ Browser #{self.browser_id} - Rezervasyon kontrol başarısız")
                                
                            except TimeoutException:
                                logging.error(f"❌ Browser #{self.browser_id} - Popup timeout")
                            except Exception as e:
                                logging.error(f"❌ Browser #{self.browser_id} - Rezervasyon hatası: {str(e)}")
                            
                    except Exception as e:
                        continue
            
            if not found_any_target:
                logging.info(f"❌ Browser #{self.browser_id} - Hiç hedef slot bulunamadı")
                
                # TÜM SLOTLARI GÖSTER
                logging.info(f"📋 Browser #{self.browser_id} - TÜM SLOTLAR LİSTESİ:")
                for i, slot in enumerate(all_slots[:10]):  # İlk 10 slot
                    try:
                        date = slot.get_attribute("data-dateformatted")
                        slot_hour = slot.get_attribute("data-hour")
                        logging.info(f"    #{i+1}: '{date}' - '{slot_hour}'")
                    except:
                        pass
            
            return False
            
        except UnexpectedAlertPresentException:
            logging.error(f"❌ Browser #{self.browser_id} - Unexpected alert hatası")
            try:
                alert = self.driver.switch_to.alert
                alert.dismiss()
            except:
                pass
            return False
            
        except TimeoutException:
            logging.error(f"❌ Browser #{self.browser_id} - Timeout hatası")
            return False
            
        except Exception as e:
            logging.error(f"❌ Browser #{self.browser_id} - Genel rezervasyon hatası: {str(e)}")
            return False
    
    def quick_success_check(self, target_date, hour):
        """Hızlı başarı kontrolü"""
        try:
            self.driver.get(f"{self.base_url}/ClubMember/MyReservation.aspx")
            time.sleep(0.5)
            
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
        
        # Daha fazla saat format denemesi
        self.preferred_hours = [
            "20:00/21:00", "19:00/20:00", "21:00/22:00", 
            "22:00/23:00", "18:00/19:00", "17:00/18:00",
            # Alternatif formatlar
            "20:00-21:00", "19:00-20:00", "21:00-22:00",
            "22:00-23:00", "18:00-19:00", "17:00-18:00"
        ]
        
        self.browser_pool = []
        
        logging.info(f"🎯 ULTIMATE DEBUG Bot - Hedef gün: {self.target_day}")
    
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
    
    def setup_debug_browser_pool(self):
        """DEBUG browser pool - sadece 1 browser"""
        logging.info("🏗️ DEBUG Browser Pool kuruluyor...")
        setup_start = time.time()
        
        max_browsers = 1  # DEBUG için tek browser
        
        def setup_single_browser_with_timeout(browser_id):
            browser = UltimateDebugBrowser(
                browser_id, self.username, self.password, 
                self.base_url, self.target_facility_url
            )
            
            if browser.quick_setup_and_login(max_time=60):
                return browser
            else:
                browser.cleanup()
                return None
        
        with ThreadPoolExecutor(max_workers=max_browsers) as executor:
            futures = [
                executor.submit(setup_single_browser_with_timeout, i+1) 
                for i in range(max_browsers)
            ]
            
            try:
                for future in as_completed(futures, timeout=90):
                    try:
                        browser = future.result()
                        if browser and browser.is_ready:
                            self.browser_pool.append(browser)
                            
                            elapsed = time.time() - setup_start
                            logging.info(f"✅ DEBUG Browser #{browser.browser_id} hazır ({elapsed:.1f}s)")
                            
                    except Exception as e:
                        logging.error(f"Browser future hatası: {str(e)}")
                        
            except TimeoutError:
                logging.error("⏰ DEBUG Browser setup timeout!")
                for f in futures:
                    f.cancel()
        
        ready_count = len(self.browser_pool)
        elapsed = time.time() - setup_start
        logging.info(f"🎯 DEBUG Browser Pool hazır: {ready_count}/1 browser ({elapsed:.1f}s)")
        
        return ready_count > 0
    
    def debug_attack(self, target_date_str):
        """DEBUG Attack"""
        if not self.browser_pool:
            logging.error("❌ Hiç DEBUG browser yok!")
            return False
        
        logging.info(f"🔬 ULTIMATE DEBUG ATTACK! {len(self.browser_pool)} browser hazır")
        
        for browser in self.browser_pool:
            result = browser.ultimate_debug_attempt(target_date_str, self.preferred_hours)
            if result:
                return True
        
        return False
    
    def cleanup_browser_pool(self):
        for browser in self.browser_pool:
            browser.cleanup()
        self.browser_pool.clear()
        logging.info("🧹 DEBUG Browser Pool temizlendi")
    
    def run_ultimate_debug(self):
        """ULTIMATE DEBUG ana fonksiyon - 9 dakika window"""
        total_start = time.time()
        
        try:
            logging.info(f"🚀 ULTIMATE DEBUG Bot başladı - {self.target_day}")
            
            target = self.calculate_target_date()
            if not target:
                logging.error("Hedef tarih hesaplanamadı")
                return
            
            logging.info(f"🎯 Hedef: {target['day_name']} - {target['turkish_date']}")
            logging.info(f"📋 Strateji: 23:54 Setup → 00:00-00:03 WAR ZONE → 9dk Total")
            
            # PHASE 1: DEBUG Browser Setup (2 dakika max)
            logging.info("⏰ Phase 1: DEBUG Browser Setup...")
            if not self.setup_debug_browser_pool():
                logging.error("❌ DEBUG Browser kurulamadı!")
                self.send_email("❌ DEBUG Bot Hatası", "DEBUG Browser kurulamadı!")
                return
            
            setup_elapsed = time.time() - total_start
            logging.info(f"✅ Phase 1 tamamlandı ({setup_elapsed:.1f}s)")
            
            # PHASE 2: WAR ZONE (00:00-00:03) - 7 dakika kalan süre
            logging.info("⏰ Phase 2: WAR ZONE - 00:00-00:03 CRITICAL TIME!")
            
            attack_start = time.time()
            max_attack_time = 540 - setup_elapsed  # 9 dakika (540s) - setup süresi
            attack_interval = 2  # 2 saniyede bir
            max_attacks = int(max_attack_time // attack_interval)
            
            attack_count = 0
            success = False
            
            while attack_count < max_attacks and not success and (time.time() - attack_start) < max_attack_time:
                attack_count += 1
                current_time = datetime.now()
                
                # WAR ZONE indicator
                if current_time.strftime('%H:%M') >= '00:00' and current_time.strftime('%H:%M') <= '00:03':
                    war_zone = "🔥 WAR ZONE 🔥"
                else:
                    war_zone = "⏳ Hazırlık"
                
                logging.info(f"⚡ Attack #{attack_count}/{max_attacks} - {current_time.strftime('%H:%M:%S')} - {war_zone}")
                
                if self.debug_attack(target['turkish_date']):
                    success = True
                    total_elapsed = time.time() - total_start
                    
                    logging.info(f"🏆 WAR ZONE VICTORY!")
                    
                    self.send_email(
                        f"🏆 WAR ZONE {target['day_name']} VICTORY!",
                        f"""🔥 WAR ZONE VICTORY!
                        
📅 Tarih: {target['turkish_date']}
🔢 Attack: #{attack_count}/{max_attacks}
⏱️ Total: {total_elapsed:.0f}s
🔥 War Zone: 00:00-00:03
⏰ Victory Time: {current_time.strftime('%H:%M:%S')}

9 dakika WAR ZONE stratejisi başarılı! 🎯"""
                    )
                    return
                
                logging.info(f"❌ Attack #{attack_count} - Slot bulunamadı")
                
                if attack_count < max_attacks:
                    time.sleep(attack_interval)
            
            # Final WAR ZONE rapor
            total_elapsed = time.time() - total_start
            
            logging.warning(f"🔥 WAR ZONE tamamlandı")
            logging.info(f"📊 Total attacks: {attack_count}")
            logging.info(f"⏱️ Total time: {total_elapsed:.0f}s")
            
            self.send_email(
                f"🔥 WAR ZONE {target['day_name']} Raporu",
                f"""🔥 WAR ZONE RAPORU
                
📅 Tarih: {target['turkish_date']}
🔢 Attacks: {attack_count}
⏱️ Total: {total_elapsed:.0f}s
🔥 War Zone: 00:00-00:03 covered
⏰ Duration: 9 dakika

WAR ZONE tam coverage ama slot alınamadı! 
Debug log'larını incele. 📊"""
            )
            
        except Exception as e:
            total_elapsed = time.time() - total_start
            logging.error(f"WAR ZONE Ana hata ({total_elapsed:.0f}s): {str(e)}")
            self.send_email("❌ WAR ZONE Hatası", f"Hata ({total_elapsed:.0f}s): {str(e)}")
        
        finally:
            self.cleanup_browser_pool()

def main():
    bot = HalisahaBot()
    bot.run_ultimate_debug()

if __name__ == "__main__":
    main()

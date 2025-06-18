#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏟️ Halısaha Rezervasyon Bot - DUAL ATTACK VERSION
WAR ZONE (00:00) + SCAVENGER MODE (03:30)
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
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
from datetime import datetime, timedelta

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def parse_turkish_date(date_str):
    """Türkçe tarihi datetime objesine çevir"""
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
    except Exception as e:
        logging.error(f"❌ Tarih parse hatası: {e}")
        return None

def is_date_in_range(target_date_str, date_range_str):
    """Hedef tarihin aralık içinde olup olmadığını kontrol et"""
    try:
        logging.info(f"🔍 Tarih kontrolü: '{target_date_str}' in '{date_range_str}'")
        
        # Basit string kontrolü önce
        if target_date_str in date_range_str:
            logging.info("✅ String eşleşmesi bulundu!")
            return True
        
        # Aralık parse et
        if " - " not in date_range_str:
            # Tek tarih
            target_dt = parse_turkish_date(target_date_str)
            range_dt = parse_turkish_date(date_range_str)
            result = target_dt == range_dt if target_dt and range_dt else False
            logging.info(f"📅 Tek tarih karşılaştırması: {result}")
            return result
        
        # Aralık var
        range_parts = date_range_str.split(" - ")
        start_date_str = range_parts[0].strip()
        end_date_str = range_parts[1].strip()
        
        logging.info(f"📅 Aralık: '{start_date_str}' - '{end_date_str}'")
        
        target_dt = parse_turkish_date(target_date_str)
        start_dt = parse_turkish_date(start_date_str)
        end_dt = parse_turkish_date(end_date_str)
        
        if target_dt and start_dt and end_dt:
            result = start_dt <= target_dt <= end_dt
            logging.info(f"📅 Aralık kontrolü: {result} ({start_dt.strftime('%d.%m')} <= {target_dt.strftime('%d.%m')} <= {end_dt.strftime('%d.%m')})")
            return result
        
        logging.error("❌ Tarih parse edilemedi")
        return False
        
    except Exception as e:
        logging.error(f"❌ Aralık kontrol hatası: {e}")
        return False

def get_navigation_direction(target_date_str, current_range_str):
    """Hangi yöne navigate edilecegini belirle"""
    try:
        if " - " not in current_range_str:
            # Tek tarih - basit karşılaştırma
            target_dt = parse_turkish_date(target_date_str)
            current_dt = parse_turkish_date(current_range_str)
            if target_dt and current_dt:
                if target_dt > current_dt:
                    return "next"
                elif target_dt < current_dt:
                    return "prev"
                else:
                    return "found"
            return "next"  # default
        
        # Aralık var
        range_parts = current_range_str.split(" - ")
        start_date_str = range_parts[0].strip()
        end_date_str = range_parts[1].strip()
        
        target_dt = parse_turkish_date(target_date_str)
        start_dt = parse_turkish_date(start_date_str)
        end_dt = parse_turkish_date(end_date_str)
        
        if target_dt and start_dt and end_dt:
            if target_dt < start_dt:
                logging.info(f"📍 Hedef ({target_dt.strftime('%d.%m')}) aralık başından ({start_dt.strftime('%d.%m')}) önce -> ÖNCEKİ")
                return "prev"
            elif target_dt > end_dt:
                logging.info(f"📍 Hedef ({target_dt.strftime('%d.%m')}) aralık sonundan ({end_dt.strftime('%d.%m')}) sonra -> SONRAKİ")
                return "next"
            else:
                logging.info(f"📍 Hedef ({target_dt.strftime('%d.%m')}) aralık içinde ({start_dt.strftime('%d.%m')}-{end_dt.strftime('%d.%m')}) -> BULUNDU")
                return "found"
        
        # Default fallback
        return "next"
        
    except Exception as e:
        logging.error(f"❌ Yön belirleme hatası: {e}")
        return "next"

def get_attack_mode():
    """Saldırı modunu belirle"""
    current_time = datetime.now()
    hour = current_time.hour
    minute = current_time.minute
    
    # WAR ZONE: 00:00-00:10
    if hour == 0 and minute <= 10:
        return "WAR_ZONE"
    
    # SCAVENGER MODE: 03:25-03:40 (biraz erken başla)
    elif hour == 3 and 25 <= minute <= 40:
        return "SCAVENGER"
    
    # MAINTENANCE: Diğer saatler
    else:
        return "STANDBY"

class DualAttackHalisahaBot:
    def __init__(self):
        self.username = os.environ.get('HALISAHA_USERNAME')
        self.password = os.environ.get('HALISAHA_PASSWORD')
        self.target_day = os.environ.get('TARGET_DAY', 'PAZARTESI')
        
        if not self.username or not self.password:
            raise ValueError("Kullanıcı bilgileri eksik!")
        
        self.base_url = "https://spor.kadikoy.bel.tr"
        self.target_facility_url = "https://spor.kadikoy.bel.tr/spor-salonu/kalamis-spor?activityCategories=2"
        
        # Prime time saatler - değişmedi! 🔥
        self.preferred_hours = [
            "20:00/21:00", "19:00/20:00", "21:00/22:00", 
            "22:00/23:00", "18:00/19:00", "17:00/18:00",
            # Alternatif formatlar
            "20:00-21:00", "19:00-20:00", "21:00-22:00",
            "22:00-23:00", "18:00-19:00", "17:00-18:00"
        ]
        
        self.driver = None
        
        logging.info(f"🎯 Dual Attack Bot hazır - Hedef gün: {self.target_day}")
    
    def calculate_target_date(self):
        """TARGET_DAY'e göre 1 hafta sonraki tarihi hesapla"""
        try:
            today = datetime.now()
            
            day_map = {
                "PAZARTESI": 0, "SALI": 1, "CARSAMBA": 2, "PERSEMBE": 3,
                "PAZARTESI".lower(): 0, "SALI".lower(): 1, 
                "CARSAMBA".lower(): 2, "PERSEMBE".lower(): 3
            }
            
            if self.target_day.upper() not in ["PAZARTESI", "SALI", "CARSAMBA", "PERSEMBE"]:
                logging.error(f"Geçersiz TARGET_DAY: {self.target_day}")
                return None
            
            target_weekday = day_map[self.target_day.upper()]
            current_weekday = today.weekday()
            
            # Dual attack için tarih hesaplama
            current_time = today.time()
            
            # Gece yarısından sonra mı kontrol et (00:00-04:00 arası)
            if current_time.hour <= 4:
                # Gece yarısı saldırı zamanı
                # Bir gün önceki akşam mı kontrol et
                yesterday_weekday = (current_weekday - 1) % 7
                
                if yesterday_weekday == (target_weekday - 1) % 7:
                    # Dün hedef günün bir gün öncesiydi, bugün 1 hafta sonraki slot açılıyor
                    days_ahead = 7
                else:
                    # Normal hesaplama
                    days_to_target = (target_weekday - current_weekday) % 7
                    if days_to_target == 0:
                        days_to_target = 7  # Aynı gün ise gelecek hafta
                    days_ahead = days_to_target + 7  # 1 hafta sonraki
            else:
                # Normal zaman
                days_to_target = (target_weekday - current_weekday) % 7
                if days_to_target == 0:
                    days_to_target = 7  # Aynı gün ise gelecek hafta
                days_ahead = days_to_target + 7  # 1 hafta sonraki
            
            target_date = today + timedelta(days=days_ahead)
            
            return {
                'day_name': self.target_day.upper(),
                'turkish_date': self.format_turkish_date(target_date),
                'date_obj': target_date
            }
        
        except Exception as e:
            logging.error(f"❌ Tarih hesaplama hatası: {e}")
            return None
    
    def format_turkish_date(self, date_obj):
        """Türkçe tarih formatı"""
        month_names = [
            "", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
        ]
        return f"{date_obj.day} {month_names[date_obj.month]} {date_obj.year}"
    
    def setup_driver(self):
        """Driver setup - GitHub Actions optimized"""
        try:
            logging.info("🔧 Driver setup başladı")
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--memory-pressure-off')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(15)
            self.driver.implicitly_wait(3)
            
            logging.info("✅ Driver hazır")
            return True
            
        except Exception as e:
            logging.error(f"❌ Driver setup hatası: {str(e)}")
            return False
    
    def login(self):
        """Login işlemi"""
        try:
            logging.info("🔐 Giriş işlemi başlatılıyor...")
            
            self.driver.get(f"{self.base_url}/giris")
            
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_field = self.driver.find_element(By.NAME, "password")
            
            # JavaScript ile değer set et (daha güvenilir)
            self.driver.execute_script(f"arguments[0].value = '{self.username}';", username_field)
            self.driver.execute_script(f"arguments[0].value = '{self.password}';", password_field)
            
            login_button = self.driver.find_element(By.ID, "btnLoginSubmit")
            self.driver.execute_script("arguments[0].click();", login_button)
            
            time.sleep(3)
            
            if "giris" not in self.driver.current_url:
                logging.info("✅ Giriş başarılı")
                return True
            else:
                logging.error("❌ Giriş başarısız")
                return False
                
        except Exception as e:
            logging.error(f"❌ Login hatası: {str(e)}")
            return False
    
    def navigate_to_facility(self):
        """Halısaha sayfasına git"""
        try:
            logging.info("🏟️ Halısaha sayfasına yönlendiriliyor...")
            
            self.driver.get(self.target_facility_url)
            time.sleep(5)  # Sayfa yüklenmesi için
            
            logging.info(f"✅ Halısaha sayfası: {self.driver.current_url}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Sayfa yönlendirme hatası: {str(e)}")
            return False
    
    def navigate_to_target_date(self, target_date_str):
        """Hedef tarihe git - Working logic"""
        try:
            logging.info(f"🗓️ Hedef tarihe navigasyon: {target_date_str}")
            
            # Alert handling
            self.dismiss_alerts()
            
            # Mevcut tarihi al
            current_date = self.driver.find_element(By.CLASS_NAME, "yonlendirme-info").text
            logging.info(f"📅 Başlangıç tarih aralığı: {current_date}")
            
            max_attempts = 15  # Daha fazla deneme
            current_attempt = 0
            
            while current_attempt < max_attempts:
                try:
                    # Fresh date check
                    current_date = self.driver.find_element(By.CLASS_NAME, "yonlendirme-info").text
                    logging.info(f"📍 Deneme {current_attempt + 1}: Mevcut tarih aralığı: '{current_date}'")
                    
                    if not current_date:
                        logging.warning("⚠️ Tarih bilgisi yok, bekleniyor...")
                        time.sleep(2)
                        current_attempt += 1
                        continue
                    
                    # Hedef tarih kontrolü
                    if is_date_in_range(target_date_str, current_date):
                        logging.info("✅ HEDEF TARİH BULUNDU! Aralık içinde.")
                        return True
                    
                    # Hangi yöne gidileceğini belirle
                    direction = get_navigation_direction(target_date_str, current_date)
                    
                    if direction == "found":
                        logging.info("✅ HEDEF TARİH BULUNDU! (Parse kontrolü)")
                        return True
                    elif direction == "prev":
                        logging.info("⬅️ Önceki haftaya geçiliyor...")
                        button = self.driver.find_element(By.ID, "area-onceki-hafta")
                        self.driver.execute_script("arguments[0].click();", button)
                    elif direction == "next":
                        logging.info("➡️ Sonraki haftaya geçiliyor...")
                        button = self.driver.find_element(By.ID, "area-sonraki-hafta")
                        self.driver.execute_script("arguments[0].click();", button)
                    
                    time.sleep(3)  # Sayfa yüklenmesi için bekle
                    current_attempt += 1
                    
                    # Alert check after navigation
                    self.dismiss_alerts()
                    
                except Exception as nav_error:
                    logging.error(f"❌ Navigasyon hatası: {nav_error}")
                    current_attempt += 1
                    time.sleep(2)
            
            logging.error(f"❌ {max_attempts} denemede hedef tarihe ulaşılamadı")
            return False
            
        except Exception as e:
            logging.error(f"❌ Tarih navigasyon genel hatası: {str(e)}")
            return False
    
    def dismiss_alerts(self):
        """Alert/popup'ları temizle"""
        try:
            alert = self.driver.switch_to.alert
            alert.dismiss()
            logging.info("🚨 Alert kapatıldı")
        except:
            pass
    
    def find_and_reserve_slot(self, target_date_str, attack_mode="WAR_ZONE"):
        """Slot bul ve rezerve et - Mode aware"""
        try:
            mode_emoji = "🔥" if attack_mode == "WAR_ZONE" else "🏴‍☠️"
            logging.info(f"{mode_emoji} {attack_mode}: Hedef tarihte slotlar aranıyor: {target_date_str}")
            time.sleep(3)
            
            # Alerts dismiss
            self.dismiss_alerts()
            
            all_slots = self.driver.find_elements(By.CSS_SELECTOR, "div.lesson.active")
            logging.info(f"📊 Toplam {len(all_slots)} aktif slot bulundu")
            
            # Debug: Tüm slotları listele
            logging.info("📋 Mevcut slotlar:")
            for i, slot in enumerate(all_slots[:10]):  # İlk 10 slot
                try:
                    date = slot.get_attribute("data-dateformatted")
                    hour = slot.get_attribute("data-hour")
                    logging.info(f"   {i+1:2d}. {date} - {hour}")
                except:
                    logging.info(f"   {i+1:2d}. Slot okunamadı")
            
            # Hedef slotu ara
            target_slot = None
            found_hour = None
            
            for test_hour in self.preferred_hours:
                logging.info(f"   🕐 Aranan saat: {test_hour}")
                for slot in all_slots:
                    try:
                        date = slot.get_attribute("data-dateformatted")
                        hour = slot.get_attribute("data-hour")
                        
                        if date == target_date_str and hour == test_hour:
                            target_slot = slot
                            found_hour = hour
                            logging.info(f"🎯 {mode_emoji} HEDEF SLOT BULUNDU: {date} - {hour}")
                            break
                    except:
                        continue
                
                if target_slot:
                    break
            
            if not target_slot:
                logging.error(f"❌ {attack_mode}: Hedef slot bulunamadı: {target_date_str}")
                
                # Sadece hedef tarih slotlarını göster
                logging.info(f"🔍 {target_date_str} tarihli tüm slotlar:")
                for slot in all_slots:
                    try:
                        date = slot.get_attribute("data-dateformatted")
                        hour = slot.get_attribute("data-hour")
                        if date == target_date_str:
                            logging.info(f"   📅 {target_date_str} slot: {hour}")
                    except:
                        continue
                
                return False
            
            # REZERVASYON İŞLEMİ
            logging.info(f"✅ {mode_emoji} Slot bulundu, rezervasyon işlemi başlatılıyor...")
            logging.info(f"📍 Slot detayı: {target_date_str} - {found_hour}")
            
            # Slot seçimi
            self.driver.execute_script("arguments[0].scrollIntoView(true);", target_slot)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", target_slot)
            logging.info("✅ Slot tıklandı")
            
            # Pop-up işlemleri
            try:
                # Pop-up'ın yüklenmesini bekle
                popup = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "bootbox"))
                )
                logging.info("✅ Pop-up yüklendi")
                
                # Rezerve Et seçeneğini bul
                rezerve_radio = popup.find_element(By.CSS_SELECTOR, "input[value='basvuru-yap']")
                self.driver.execute_script("arguments[0].click();", rezerve_radio)
                logging.info("✅ Rezerve Et seçeneği seçildi")
                
                # Devam butonunu bul ve tıkla
                devam_button = popup.find_element(By.CSS_SELECTOR, "button.btn.btn-blue.devam-et")
                self.driver.execute_script("arguments[0].click();", devam_button)
                logging.info("✅ Devam butonuna tıklandı")
                
                # İkinci pop-up için bekle
                time.sleep(2)
                
                # Rezervasyon kuralları checkbox'ını bul
                rules_checkbox = self.driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                self.driver.execute_script("arguments[0].click();", rules_checkbox)
                logging.info("✅ Rezervasyon kuralları kabul edildi")
                
                # Evet butonunu bul ve tıkla
                self.driver.execute_script("""
                    var buttons = document.querySelectorAll('button.btn.btn-blue');
                    for(var i=0; i<buttons.length; i++) {
                        if(buttons[i].textContent.trim() === 'Evet') {
                            buttons[i].click();
                            return true;
                        }
                    }
                """)
                logging.info("✅ Final 'Evet' butonu tıklandı")
                
                # Tıklama sonrası bekle
                time.sleep(5)
                
                # Rezervasyon kontrolü
                success = self.check_reservation_success(target_date_str, found_hour)
                
                if success:
                    logging.info(f"🎉 ✅ {mode_emoji} REZERVASYON BAŞARIYLA TAMAMLANDI!")
                    return True
                else:
                    logging.error(f"❌ {attack_mode}: Rezervasyon tamamlanamadı veya doğrulanamadı!")
                    return False
                    
            except Exception as popup_error:
                logging.error(f"❌ {attack_mode}: Pop-up işlemlerinde hata: {str(popup_error)}")
                return False
            
        except Exception as e:
            logging.error(f"❌ {attack_mode}: Slot bulma/rezervasyon genel hatası: {str(e)}")
            return False
    
    def check_reservation_success(self, target_date_str, target_hour):
        """Rezervasyonun başarılı olup olmadığını kontrol et"""
        try:
            logging.info(f"🔍 Rezervasyon kontrolü: {target_date_str} - {target_hour}")
            
            # Rezervasyonlarım sayfasına git
            self.driver.get(f"{self.base_url}/ClubMember/MyReservation.aspx")
            time.sleep(3)
            
            # Tablodaki tüm satırları bul
            rows = self.driver.find_elements(By.CSS_SELECTOR, "#AreaReservationTable tbody tr")
            logging.info(f"📊 Tabloda {len(rows)} satır bulundu")
            
            # Tarih formatını rezervasyon kontrol için düzenle
            target_dt = parse_turkish_date(target_date_str)
            if target_dt:
                check_date = target_dt.strftime("%d.%m.%Y")
                short_date = target_dt.strftime("%d.%m")
            else:
                check_date = target_date_str
                short_date = target_date_str
            
            check_hour = target_hour.replace("/", " - ") if target_hour else ""
            
            logging.info(f"🔍 Aranan: {check_date} - {check_hour}")
            
            # Her satırı kontrol et
            for i, row in enumerate(rows):
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 5:
                        date_cell = cells[2].text if len(cells) > 2 else ""
                        hour_cell = cells[3].text if len(cells) > 3 else ""
                        status = cells[4].text if len(cells) > 4 else ""
                        
                        logging.info(f"📋 Satır {i+1}: {date_cell} | {hour_cell} | {status}")
                        
                        # Tarih ve saat kontrolü
                        date_match = (check_date in date_cell or short_date in date_cell or target_date_str in date_cell)
                        hour_match = check_hour in hour_cell if check_hour else True
                        
                        if date_match and hour_match:
                            logging.info(f"✅ Rezervasyon bulundu:")
                            logging.info(f"   Tarih: {date_cell}")
                            logging.info(f"   Saat: {hour_cell}")
                            logging.info(f"   Durum: {status}")
                            
                            if "Ön Onaylı" in status or "Onaylı" in status:
                                return True
                            
                except Exception as row_error:
                    logging.error(f"⚠️ Satır {i+1} okuma hatası: {str(row_error)}")
                    continue
            
            return False
            
        except Exception as e:
            logging.error(f"❌ Rezervasyon kontrolü hatası: {str(e)}")
            return False
    
    def send_email(self, subject, message):
        """Email gönder"""
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
    
    def wait_for_scavenger_mode(self):
        """SCAVENGER MODE zamanını bekle"""
        current_time = datetime.now()
        
        # 03:25'e kadar bekle
        target_time = current_time.replace(hour=3, minute=25, second=0, microsecond=0)
        
        # Eğer şu an 03:25'ten sonraysa, yarın 03:25'i bekle
        if current_time.time() > target_time.time():
            target_time += timedelta(days=1)
        
        wait_seconds = (target_time - current_time).total_seconds()
        
        if wait_seconds > 0:
            logging.info(f"⏳ SCAVENGER MODE için bekleniyor: {wait_seconds:.0f} saniye ({target_time.strftime('%H:%M:%S')})")
            time.sleep(wait_seconds)
    
    def run_dual_attack(self):
        """DUAL ATTACK ana fonksiyon - WAR ZONE + SCAVENGER MODE"""
        start_time = time.time()
        
        try:
            # Hedef tarih hesapla
            target = self.calculate_target_date()
            if not target:
                raise Exception("Hedef tarih hesaplanamadı")
            
            logging.info(f"🚀 DUAL ATTACK Halısaha Bot başladı - {self.target_day}")
            logging.info(f"🎯 Hedef: {target['day_name']} - {target['turkish_date']}")
            logging.info("🔥 WAR ZONE (00:00-00:05) + 🏴‍☠️ SCAVENGER MODE (03:30-03:35)")
            logging.info("="*60)
            
            # Attack mode belirle
            attack_mode = get_attack_mode()
            current_time = datetime.now()
            
            logging.info(f"⏰ Başlangıç zamanı: {current_time.strftime('%H:%M:%S')}")
            logging.info(f"🎯 Attack Mode: {attack_mode}")
            
            # Driver setup
            if not self.setup_driver():
                raise Exception("Driver setup başarısız")
            
            # Login
            if not self.login():
                raise Exception("Login başarısız")
            
            # Halısaha sayfasına git
            if not self.navigate_to_facility():
                raise Exception("Sayfa yönlendirme başarısız")
            
            success = False
            
            # PHASE 1: WAR ZONE (00:00-00:05)
            if attack_mode == "WAR_ZONE" or current_time.hour == 0:
                logging.info("🔥 WAR ZONE BAŞLADI!")
                
                attack_start = time.time()
                max_attack_time = 300  # 5 dakika (300 saniye)
                attack_interval = 3  # 3 saniyede bir
                max_attacks = int(max_attack_time // attack_interval)
                
                attack_count = 0
                
                while attack_count < max_attacks and not success and (time.time() - attack_start) < max_attack_time:
                    attack_count += 1
                    attack_time = datetime.now()
                    
                    logging.info(f"🔥 WAR ZONE Attack #{attack_count}/{max_attacks} - {attack_time.strftime('%H:%M:%S')}")
                    
                    # Hedef tarihe git ve slot ara
                    if self.navigate_to_target_date(target['turkish_date']):
                        if self.find_and_reserve_slot(target['turkish_date'], "WAR_ZONE"):
                            success = True
                            total_elapsed = time.time() - start_time
                            
                            logging.info(f"🏆 WAR ZONE VICTORY!")
                            
                            self.send_email(
                                f"🔥 {target['day_name']} WAR ZONE VICTORY!",
                                f"""🔥 WAR ZONE VICTORY!
                                
📅 Tarih: {target['turkish_date']} ({target['day_name']})
🔢 Attack: #{attack_count}/{max_attacks}
⏱️ Total: {total_elapsed:.0f}s
🔥 Phase: WAR ZONE (00:00-00:05)
⏰ Victory Time: {attack_time.strftime('%H:%M:%S')}
🏟️ Tesis: Kalamış Spor Tesisi

İlk saldırıda başarı! 🎯"""
                            )
                            return
                    
                    if attack_count < max_attacks:
                        time.sleep(attack_interval)
                
                if not success:
                    logging.warning("🔥 WAR ZONE tamamlandı - Başarısız")
                    logging.info("🏴‍☠️ SCAVENGER MODE'a hazırlanılıyor...")
            
            # PHASE 2: SCAVENGER MODE için bekle ve saldır
            if not success:
                # Eğer henüz SCAVENGER zamanı değilse bekle
                if attack_mode == "STANDBY":
                    self.wait_for_scavenger_mode()
                
                logging.info("🏴‍☠️ SCAVENGER MODE BAŞLADI!")
                logging.info("🏴‍☠️ Düşen rezervasyonları avcılama zamanı!")
                
                scavenger_start = time.time()
                max_scavenger_time = 600  # 10 dakika (600 saniye)
                scavenger_interval = 5  # 5 saniyede bir (daha az agresif)
                max_scavenger_attacks = int(max_scavenger_time // scavenger_interval)
                
                scavenger_count = 0
                
                while scavenger_count < max_scavenger_attacks and not success and (time.time() - scavenger_start) < max_scavenger_time:
                    scavenger_count += 1
                    scavenger_time = datetime.now()
                    
                    logging.info(f"🏴‍☠️ SCAVENGER Attack #{scavenger_count}/{max_scavenger_attacks} - {scavenger_time.strftime('%H:%M:%S')}")
                    
                    # Hedef tarihe git ve düşen slotları ara
                    if self.navigate_to_target_date(target['turkish_date']):
                        if self.find_and_reserve_slot(target['turkish_date'], "SCAVENGER"):
                            success = True
                            total_elapsed = time.time() - start_time
                            
                            logging.info(f"🏆 SCAVENGER VICTORY!")
                            
                            self.send_email(
                                f"🏴‍☠️ {target['day_name']} SCAVENGER VICTORY!",
                                f"""🏴‍☠️ SCAVENGER MODE VICTORY!
                                
📅 Tarih: {target['turkish_date']} ({target['day_name']})
🔢 Attack: #{scavenger_count}/{max_scavenger_attacks}
⏱️ Total: {total_elapsed:.0f}s
🏴‍☠️ Phase: SCAVENGER MODE (03:30+)
⏰ Victory Time: {scavenger_time.strftime('%H:%M:%S')}
🏟️ Tesis: Kalamış Spor Tesisi

Düşen rezervasyonu kaptık! 🎯"""
                            )
                            return
                    
                    if scavenger_count < max_scavenger_attacks:
                        time.sleep(scavenger_interval)
            
            # Final rapor
            if not success:
                total_elapsed = time.time() - start_time
                
                logging.warning(f"❌ DUAL ATTACK tamamlandı - Başarısız")
                
                self.send_email(
                    f"📊 {target['day_name']} DUAL ATTACK Raporu",
                    f"""📊 DUAL ATTACK RAPORU - {target['day_name']}
                    
📅 Tarih: {target['turkish_date']}
⏱️ Total: {total_elapsed:.0f}s
🔥 WAR ZONE: 00:00-00:05 (İlk saldırı)
🏴‍☠️ SCAVENGER: 03:30+ (Düşen rezervasyonlar)

Her iki saldırıda da slot alınamadı.
Çok yoğun rekabet veya slot mevcut değil. 📊"""
                )
            
        except Exception as e:
            total_elapsed = time.time() - start_time
            logging.error(f"DUAL ATTACK Ana hata ({total_elapsed:.0f}s): {str(e)}")
            self.send_email(
                f"❌ {self.target_day} DUAL ATTACK Hatası", 
                f"Hata ({total_elapsed:.0f}s): {str(e)}"
            )
        
        finally:
            # Cleanup
            if self.driver:
                try:
                    logging.info(f"📍 Son URL: {self.driver.current_url}")
                    self.driver.save_screenshot(f"dual_attack_{self.target_day.lower()}_result.png")
                    logging.info("📸 Ekran görüntüsü kaydedildi")
                except:
                    logging.warning("⚠️ Ekran görüntüsü kaydedilemedi")
                
                self.driver.quit()
                logging.info("🔒 Browser kapatıldı")

def main():
    target_day = os.environ.get('TARGET_DAY', 'PAZARTESI')
    logging.info(f"🏟️ DUAL ATTACK Halısaha Bot")
    logging.info(f"🎯 Hedef Gün: {target_day}")
    logging.info(f"🔥 WAR ZONE (00:00) + 🏴‍☠️ SCAVENGER (03:30)")
    logging.info("="*60)
    
    bot = DualAttackHalisahaBot()
    bot.run_dual_attack()

if __name__ == "__main__":
    main()

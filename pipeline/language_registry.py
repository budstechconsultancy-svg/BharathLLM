import os

INDIAN_LANGUAGES = {
  "hi": {
    "name": "Hindi",
    "tesseract_code": "hin",
    "unicode_ranges": [(0x0900, 0x097F)],   # Devanagari
    "script": "Devanagari",
    "states": ["UP","RJ","HR","MP","BR","JH","CG","UK","HP","DL","CT"],
    "central_govt": True,
    "official_lang": True
  },
  "ta": {
    "name": "Tamil",
    "tesseract_code": "tam",
    "unicode_ranges": [(0x0B80, 0x0BFF)],
    "script": "Tamil",
    "states": ["TN","PY"],
    "central_govt": False,
    "official_lang": True
  },
  "te": {
    "name": "Telugu",
    "tesseract_code": "tel",
    "unicode_ranges": [(0x0C00, 0x0C7F)],
    "script": "Telugu",
    "states": ["AP","TS"],
    "central_govt": False,
    "official_lang": True
  },
  "kn": {
    "name": "Kannada",
    "tesseract_code": "kan",
    "unicode_ranges": [(0x0C80, 0x0CFF)],
    "script": "Kannada",
    "states": ["KA"],
    "central_govt": False,
    "official_lang": True
  },
  "ml": {
    "name": "Malayalam",
    "tesseract_code": "mal",
    "unicode_ranges": [(0x0D00, 0x0D7F)],
    "script": "Malayalam",
    "states": ["KL","LD"],
    "central_govt": False,
    "official_lang": True
  },
  "bn": {
    "name": "Bengali",
    "tesseract_code": "ben",
    "unicode_ranges": [(0x0980, 0x09FF)],
    "script": "Bengali",
    "states": ["WB","TR"],
    "central_govt": False,
    "official_lang": True
  },
  "mr": {
    "name": "Marathi",
    "tesseract_code": "mar",
    "unicode_ranges": [(0x0900, 0x097F)],   # Also Devanagari
    "script": "Devanagari",
    "states": ["MH","DD"],
    "central_govt": False,
    "official_lang": True
  },
  "gu": {
    "name": "Gujarati",
    "tesseract_code": "guj",
    "unicode_ranges": [(0x0A80, 0x0AFF)],
    "script": "Gujarati",
    "states": ["GJ","DD","DN"],
    "central_govt": False,
    "official_lang": True
  },
  "pa": {
    "name": "Punjabi",
    "tesseract_code": "pan",
    "unicode_ranges": [(0x0A00, 0x0A7F)],   # Gurmukhi
    "script": "Gurmukhi",
    "states": ["PB","CH"],
    "central_govt": False,
    "official_lang": True
  },
  "or": {
    "name": "Odia",
    "tesseract_code": "ori",
    "unicode_ranges": [(0x0B00, 0x0B7F)],
    "script": "Odia",
    "states": ["OD"],
    "central_govt": False,
    "official_lang": True
  },
  "as": {
    "name": "Assamese",
    "tesseract_code": "asm",
    "unicode_ranges": [(0x0980, 0x09FF)],   # Bengali script
    "script": "Bengali",
    "states": ["AS"],
    "central_govt": False,
    "official_lang": True
  },
  "ur": {
    "name": "Urdu",
    "tesseract_code": "urd",
    "unicode_ranges": [(0x0600, 0x06FF),(0x0750, 0x077F)],  # Arabic + supplement
    "script": "Nastaliq",
    "states": ["JK","TS","UP"],
    "rtl": True,
    "central_govt": True,
    "official_lang": True
  },
  "sa": {
    "name": "Sanskrit",
    "tesseract_code": "san",
    "unicode_ranges": [(0x0900, 0x097F)],
    "script": "Devanagari",
    "states": ["ALL"],
    "central_govt": True,
    "official_lang": True
  },
  "mni": {
    "name": "Manipuri/Meitei",
    "tesseract_code": "mni",
    "unicode_ranges": [(0xABC0, 0xABFF),(0x0980, 0x09FF)],  # Meitei Mayek + Bengali
    "script": "Meitei_Mayek",
    "states": ["MN"],
    "central_govt": False,
    "official_lang": True
  },
  "kok": {
    "name": "Konkani",
    "tesseract_code": "kok",
    "unicode_ranges": [(0x0900, 0x097F)],
    "script": "Devanagari",
    "states": ["GA"],
    "central_govt": False,
    "official_lang": True
  },
  "ne": {
    "name": "Nepali",
    "tesseract_code": "nep",
    "unicode_ranges": [(0x0900, 0x097F)],
    "script": "Devanagari",
    "states": ["SK","WB"],
    "central_govt": False,
    "official_lang": True
  },
  "doi": {
    "name": "Dogri",
    "tesseract_code": "dog",
    "unicode_ranges": [(0x0900, 0x097F)],
    "script": "Devanagari",
    "states": ["JK"],
    "central_govt": False,
    "official_lang": True
  },
  "bho": {
    "name": "Bodo",
    "tesseract_code": "bod",
    "unicode_ranges": [(0x0900, 0x097F)],
    "script": "Devanagari",
    "states": ["AS"],
    "central_govt": False,
    "official_lang": True
  },
  "mai": {
    "name": "Maithili",
    "tesseract_code": "mai",
    "unicode_ranges": [(0x0900, 0x097F)],
    "script": "Devanagari",
    "states": ["BR","JH"],
    "central_govt": False,
    "official_lang": True
  },
  "sd": {
    "name": "Sindhi",
    "tesseract_code": "snd",
    "unicode_ranges": [(0x0600, 0x06FF)],   # Arabic script
    "script": "Arabic",
    "states": ["RJ","GJ"],
    "rtl": True,
    "central_govt": False,
    "official_lang": True
  },
  "sat": {
    "name": "Santali",
    "tesseract_code": "sat",
    "unicode_ranges": [(0x1C50, 0x1C7F)],   # OL Chiki script
    "script": "OL Chiki",
    "states": ["JH","WB","AS","OR"],
    "central_govt": False,
    "official_lang": True
  },
  "ks": {
    "name": "Kashmiri",
    "tesseract_code": "kas",
    "unicode_ranges": [(0x0600, 0x06FF)],   # Arabic/Perso-Arabic script
    "script": "Arabic",
    "states": ["JK"],
    "rtl": True,
    "central_govt": False,
    "official_lang": True
  },
  "en": {
    "name": "English",
    "tesseract_code": "eng",
    "unicode_ranges": [(0x0041, 0x007A)],
    "script": "Latin",
    "states": ["ALL"],
    "central_govt": True,
    "official_lang": True
  }
}

def get_deployment_languages(deployment_state: str, deployment_mode: str) -> list:
  """
  Returns ordered list of language codes for a given deployment.
  Priority: state primary language > Hindi > English > other Indian languages
  """
  primary = os.getenv("PRIMARY_LANGUAGES", "hi,en").split(",")
  all_langs = list(INDIAN_LANGUAGES.keys())
  # Put primary languages first, then rest
  ordered = primary + [l for l in all_langs if l not in primary]
  return ordered

def get_ocr_lang_string(deployment_state: str) -> str:
  """
  Returns tesseract lang string for this deployment.
  e.g. "tam+hin+eng" for Tamil Nadu, "hin+eng" for Central Govt
  """
  primary = os.getenv("PRIMARY_LANGUAGES", "hi,en").split(",")
  # Always include primary + hindi + english as minimum
  codes = set()
  for lang_code in primary:
    if lang_code in INDIAN_LANGUAGES:
      codes.add(INDIAN_LANGUAGES[lang_code]["tesseract_code"])
  # Always ensure eng and hin are present
  codes.add("eng")
  codes.add("hin")
  return "+".join(sorted(codes))

def detect_scripts_present(text: str) -> dict:
  """
  Scan text and return which Indian scripts are present.
  Returns: {lang_code: True/False}
  """
  results = {}
  for lang_code, info in INDIAN_LANGUAGES.items():
    for start, end in info["unicode_ranges"]:
      if any(start <= ord(c) <= end for c in text):
        results[lang_code] = True
        break
    else:
      results[lang_code] = False
  return {k: v for k, v in results.items() if v}  # only present scripts

INDIAN_NUMERAL_MAP = {
  # Devanagari (Hindi, Marathi, Sanskrit, Nepali, etc.)
  "०":"0","१":"1","२":"2","३":"3","४":"4",
  "५":"5","६":"6","७":"7","८":"8","९":"9",
  # Tamil
  "௦":"0","௧":"1","௨":"2","௩":"3","௪":"4",
  "௫":"5","௬":"6","௭":"7","௮":"8","௯":"9",
  # Telugu
  "౦":"0","౧":"1","౨":"2","౩":"3","౪":"4",
  "౫":"5","౬":"6","౭":"7","౮":"8","౯":"9",
  # Kannada
  "೦":"0","೧":"1","೨":"2","೩":"3","೪":"4",
  "೫":"5","೬":"6","೭":"7","೮":"8","೯":"9",
  # Malayalam
  "൦":"0","൧":"1","൨":"2","൩":"3","൪":"4",
  "൫":"5","൬":"6","൭":"7","🎖":"8","൯":"9",
  # Bengali/Assamese
  "০":"0","১":"1","২":"2","৩":"3","৪":"4",
  "৫":"5","৬":"6","৭":"7","৮":"8","৯":"9",
  # Gujarati
  "૦":"0","૧":"1","૨":"2","૩":"3","૪":"4",
  "૫":"5","૬":"6","૭":"7","૮":"8","૯":"9",
  # Punjabi/Gurmukhi
  "੦":"0","੧":"1","੨":"2","੩":"3","੪":"4",
  "੫":"5","੬":"6","੭":"7","੮":"8","੯":"9",
  # Odia
  "୦":"0","୧":"1","୨":"2","୩":"3","୪":"4",
  "୫":"5","୬":"6","୭":"7","୮":"8","୯":"9",
  # Urdu/Arabic-Indic
  "٠":"0","١":"1","٢":"2","٣":"3","٤":"4",
  "٥":"5","٦":"6","٧":"7","٨":"8","٩":"9"
}

def normalise_numerals(text: str) -> str:
  """Convert all Indian script numerals to ASCII digits."""
  for indic, arabic in INDIAN_NUMERAL_MAP.items():
    text = text.replace(indic, arabic)
  return text

MONTH_NAMES_INDIAN = {
  # Hindi months
  "जनवरी":"01","फरवरी":"02","मार्च":"03","अप्रैल":"04",
  "मई":"05","जून":"06","जुलाई":"07","अगस्त":"08",
  "सितम्बर":"09","अक्टूबर":"10","नवम्बर":"11","दिसम्बर":"12",
  # Tamil months
  "ஜனவரி":"01","பிப்ரவரி":"02","மார்ச்":"03","ஏப்ரல்":"04",
  "மே":"05","ஜூன்":"06","ஜூலை":"07","ஆகஸ்ட்":"08",
  "செப்டம்பர்":"09","அக்டோபர்":"10","நவம்பர்":"11","டிசம்பர்":"12",
  # Telugu months
  "జనవరి":"01","ఫిబ్రవరి":"02","మార్చి":"03","ఏప్రిల్":"04",
  "మే":"05","జూన్":"06","జూలై":"07","ఆగస్టు":"08",
  "సెప్టెంబర్":"09","అక్టోబర్":"10","నవంబర్":"11","డిసेंबर":"12",
  # Kannada months
  "ಜನವರಿ":"01","ಫೆಬ್ರವರಿ":"02","ಮಾರ್ಚ್":"03","ಏಪ್ರಿಲ್":"04",
  "ಮೇ":"05","ಜೂನ್":"06","ಜುಲೈ":"07","ಆಗಸ್ಟ್":"08",
  "ಸೆಪ್ಟೆಂಬರ್":"09","ಅಕ್ಟೋಬರ್":"10","ನವೆಂಬರ್":"11","ಡಿಸೆಂಬರ್":"12",
  # Malayalam months
  "ജനുവരി":"01","ഫെബ്രുവരി":"02","മാർച്ച്":"03","ഏപ്രിൽ":"04",
  "മേയ്":"05","ജൂൺ":"06","ജൂലൈ":"07","ഓഗസ്റ്റ്":"08",
  "സെപ്റ്റംਬਰ":"09","ഒക്ടോബർ":"10","നവംਬਰ":"11","ഡിസംബർ":"12",
  # Bengali months
  "জানুয়ারি":"01","ফেব্রুয়ারি":"02","মার্চ":"03","এপ্রিল":"04",
  "মে":"05","জুন":"06","জুলাই":"07","আগস্ট":"08",
  "সেপ্টেম্বর":"09","অক্টোবর":"10","নভেম্বর":"11","ডিসেম্বর":"12",
  # Marathi months
  "जानेवारी":"01","फेब्रुवारी":"02","मार्च":"03","एप्रिल":"04",
  "मे":"05","जून":"06","जुलै":"07","ऑगस्ट":"08",
  "सप्टेंबर":"09","ऑक्टोबर":"10","नोव्हेंबर":"11","डिसेंबर":"12",
  # Gujarati months
  "જાન્યુઆરી":"01","ફેબ્રુઆરી":"02","માર્ચ":"03","એપ્રિલ":"04",
  "મે":"05","જૂન":"06","જુલાઈ":"07","ઓગસ્ટ":"08",
  "સપ્ટેમ્બર":"09","ઓક્ટોબર":"10","નવેમ્બર":"11","ડિસેમ્બર":"12",
  # Punjabi months
  "ਜਨਵਰੀ":"01","ਫਰਵਰੀ":"02","ਮਾਰਚ":"03","ਅਪ੍ਰੈਲ":"04",
  "ਮਈ":"05","ਜੂਨ":"06","ਜੁਲਾਈ":"07","ਅਗਸਤ":"08",
  "ਸਤੰਬਰ":"09","ਅਕਤੂਬਰ":"10","ਨਵੰਬਰ":"11","ਦਸੰਬਰ":"12",
}

SAKA_ERA_OFFSET = 78  # Saka year + 78 = Gregorian year (approx)

def convert_saka_date(saka_year: int, month_num: int, day: int) -> str:
  """Convert Saka Era date (used in Indian Gazette) to Gregorian."""
  gregorian_year = saka_year + SAKA_ERA_OFFSET
  return f"{gregorian_year}-{month_num:02d}-{day:02d}"

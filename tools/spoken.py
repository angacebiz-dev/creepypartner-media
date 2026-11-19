"""Turn numbers into the words a narrator would say, BEFORE they go to the TTS.
Kokoro reads "1965" as "nineteen hundred sixty five". We want "nineteen sixty five".
  1965 -> nineteen sixty five      1905 -> nineteen oh five     1900 -> nineteen hundred
  2007 -> two thousand seven       2020 -> twenty twenty        1960s -> nineteen sixties
  '60s -> sixties                  7 BC -> seven B C            Dec. 9 -> December 9 (left to Kokoro)
Usage: from spoken import say;  say("In 1965, ...")
"""
import re

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
PLURAL_TENS = {"twenty": "twenties", "thirty": "thirties", "forty": "forties", "fifty": "fifties",
               "sixty": "sixties", "seventy": "seventies", "eighty": "eighties", "ninety": "nineties"}


def two(n):
    if n < 20:
        return ONES[n]
    t, o = divmod(n, 10)
    return TENS[t] + ("" if o == 0 else " " + ONES[o])


def year(n):
    if 2000 <= n <= 2009:
        return "two thousand" + ("" if n == 2000 else " " + ONES[n - 2000])
    hi, lo = divmod(n, 100)
    if lo == 0:
        return two(hi) + " hundred"
    if lo < 10:
        return two(hi) + " oh " + ONES[lo]
    return two(hi) + " " + two(lo)


def decade(n):  # 1960 -> nineteen sixties, 1900 -> nineteen hundreds
    hi, lo = divmod(n, 100)
    if lo == 0:
        return two(hi) + " hundreds"
    w = two(lo)
    return two(hi) + " " + PLURAL_TENS.get(w, w + "s")



# names espeak gets wrong -> respellings (checked with kokoro_onnx Tokenizer, en-us)
PRON = {"Hokkaido": "Hoh kydoh", "Quesnel": "Kwuhnell", "Okiku": "Ohkeeku", "Eikichi": "Eh-kee-chee",
        "Tavernier": "Tavernyay", "Bagans": "Baygans", "Toschi": "Toskee", "Estes": "Esteez", "Ina": "Eyena", "Francisville": "Fransisville", "Villisca": "Vuh-Lisska"}

def say(text):
    for k, v in PRON.items():
        text = re.sub(r"\b%s\b" % k, v, text)
    text = re.sub(r"\b(1[0-9]{2}|20[0-9])0s\b", lambda m: decade(int(m.group(1) + "0")), text)
    text = re.sub(r"\b(1[0-9]{3}|20[0-9]{2})(?!\d)", lambda m: year(int(m.group(1))), text)
    text = re.sub(r"[‘']([2-9])0s\b", lambda m: PLURAL_TENS[TENS[int(m.group(1))]], text)
    text = re.sub(r"\b(\d{1,3})\s?(BC|AD|BCE|CE)\b", lambda m: two(int(m.group(1))) + " " + " ".join(m.group(2)) if int(m.group(1)) < 100 else m.group(0), text)
    return text


if __name__ == "__main__":
    for s in ["1965", "In the late 1960s, a killer", "1905", "1900s", "2007", "2020", "1817.", "1735,", "the '60s", "7 BC", "1200 feet"]:
        print(s, "->", say(s))

from nlu.intent_classifier import classify_intent
from nlu.slot_filler       import extract_slots

def main():
    txt    = "Crea un muro de 5m entre ejes 1 y 2"
    intent = classify_intent(txt)
    slots  = extract_slots(txt, intent)
    print("Intent:", intent)
    print("Slots :", slots)

if __name__ == "__main__":
    main()
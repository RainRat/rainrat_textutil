from charset_normalizer import from_bytes

def check(text, enc):
    data = text.encode(enc)
    guess = from_bytes(data).best()
    print(f"Enc: {enc}, Len: {len(data)}, Guess: {guess.encoding if guess else 'None'}")

check("Hello", "utf-16-le")
check("Hello", "utf-16-be")
check("Hello World", "utf-16-le")
check("Hello World", "utf-16-be")

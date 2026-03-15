from charset_normalizer import from_bytes

def check(text, enc):
    data = text.encode(enc)
    guess = from_bytes(data).best()
    print(f"Text: '{text}', Enc: {enc}, Data: {data.hex(' ')}, Guess: {guess.encoding if guess else 'None'}, Prob: {guess.coherence if guess else 0}")

check("Hello World! How are you today?", "utf-16-le")
check("Hello World! How are you today?", "utf-16-be")

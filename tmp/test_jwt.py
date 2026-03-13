
from jose import jwt
import os

# Segments: {"alg":"HS256","typ":"JWT"}, {}, signature
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-x9Gv7pD6S7S-3S7S-3S7S-3S7S-3S7S-3S7S-3S7"
secret = "secret"

def test(name, algorithms):
    print(f"--- {name} (algorithms={algorithms}) ---")
    try:
        jwt.decode(token, secret, algorithms=algorithms)
        print("RESULT: SUCCESS")
    except Exception as e:
        print(f"RESULT: FAILED - {type(e).__name__}: {str(e)}")

test("HS256 ONLY", ["HS256"])
test("HS256 AND RS256", ["HS256", "RS256"])
test("RS256 ONLY", ["RS256"])

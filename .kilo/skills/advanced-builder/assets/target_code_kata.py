# TASK: Fix is_palindrome to be case-insensitive and ignore non-alphanumeric
def is_palindrome(s: str) -> bool:
    # buggy: case-sensitive and does not ignore non-alnum
    return s == s[::-1]

def test_is_palindrome():
    assert is_palindrome("racecar") == True
    assert is_palindrome("Racecar") == True
    assert is_palindrome("A man, a plan, a canal: Panama") == True
    assert is_palindrome("hello") == False
    print("TEST_PASS")

if __name__ == "__main__":
    test_is_palindrome()

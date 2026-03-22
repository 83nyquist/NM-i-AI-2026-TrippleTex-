def is_valid_norwegian_bank_account(account_number):
    if len(account_number) != 11 or not account_number.isdigit():
        return False
    weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    checksum = sum(int(digit) * weight for digit, weight in zip(account_number[:10], weights))
    remainder = checksum % 11
    if remainder == 0:
        check_digit = 0
    else:
        check_digit = 11 - remainder
    if check_digit == 10:
        return False
    return check_digit == int(account_number[10])

for i in range(10000000000, 10000001000):
    if is_valid_norwegian_bank_account(str(i)):
        print(i)
        break

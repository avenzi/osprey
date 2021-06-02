

def validate_input(message, expecting, case=False):
    """
    Rudimentary user input validation
    <message> input message to be displayed
    <expecting> List of expected strings
    <case> Bool, whether case sensitive. If False, answer is always converted to lower case.
    """
    # TODO: add regex option to the <expecting> argument
    if not case:  # not case sensitive
        expecting = [s.lower() for s in expecting]

    while True:
        ans = input(message).strip()
        if not case:
            ans = ans.lower()
        if ans in expecting:  # valid
            break
        else:  # invalid
            print("Invalid input. Expecting: {}".format(expecting))

    return ans
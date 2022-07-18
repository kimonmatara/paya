def getKnotList(numCVs, degree):
    numbers = list(range(numCVs-(degree-1)))
    head = [numbers[0]] * degree
    tail = [numbers[-1]] * degree
    return head + numbers[1:-1] + tail
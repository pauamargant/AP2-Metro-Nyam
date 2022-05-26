# PER GUARDAR FUNCIONS NO USADES PER SI DE CAS
def perform_operation(rests: Restaurants, operator: str, operand_1: Operand, operand_2: Operand) -> Restaurants:
    '''
        Given an operator and one/two operands performs the operation on the opperand/s.
        Given an operator, if it's either "or" or "and" it performs the operation between the two
        operands. If it's "not" only one operand is needed.

        Operations are performed between lists of restaurants. If an operand is a string (a query) then
        it is replaced with the according list of restaurants. 
        The "not" operation is defined as the complement of the operand in set of all restaurants.

        Parameters
        ----------
        rests: Restaurants
        operator: str
        operand_1: Operand
        operand_2: Operand

        Returns
        -------
        Restaurants
    '''

    # The operands can be either a query (string) or a list of restaurants. If it's a query, we solve it and s
    # substitute it by the according list of restaurants
    if (operand_1 and isinstance(operand_1, str)):
        operand_1 = search_in_rsts(operand_1, rests)
    if (operand_2 and isinstance(operand_2, str)):
        operand_2 = search_in_rsts(operand_2, rests)
    if operator == "and":
        return list(set(operand_1).intersection(operand_2))
    if operator == "or":
        return list(set(operand_1).union(operand_2))
    if operator == "not":
        return list(set(rests) - set(operand_1))
    return []

/// GBNF (Grammar-Based Normalization Form) for RawStateVector.
/// Forces the LLM to output a strict JSON with specific keys and integer values.
///
/// Target JSON: {"a":12, "f":33, "s":0, "p":50, "i":80, "w":15, "t":1}
const String stateVectorGrammar = r'''
root   ::= object
object ::= "{" ws pair_a "," ws pair_f "," ws pair_s "," ws pair_p "," ws pair_i "," ws pair_w "," ws pair_t "}"

pair_a ::= """a""" ":" ws number
pair_f ::= """f""" ":" ws number
pair_s ::= """s""" ":" ws number
pair_p ::= """p""" ":" ws number
pair_i ::= """i""" ":" ws number
pair_w ::= """w""" ":" ws number
pair_t ::= """t""" ":" ws tone_enum

number ::= [0-9]+
tone_enum ::= [0-3]
ws     ::= [ \t\n]*
''';
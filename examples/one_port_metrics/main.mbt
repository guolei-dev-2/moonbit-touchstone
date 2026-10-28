///|
fn main raise {
  // Finite physical Z in ohms (Touchstone 2.1), referred to 50 ohms.
  // Short, matched, mismatched, active and complex passive reflection.
  let text = "[Version] 2.1\n# Hz Z RI R 50\n[Number of Ports] 1\n[Number of Frequencies] 5\n[Network Data]\n1000000000 0 0\n2000000000 50 0\n3000000000 150 0\n4000000000 -150 0\n5000000000 50 50\n[End]\n"
  let metrics = @rf.parse(text).network_only().metrics(0, 0)
  // On a one-port the output=input choice makes the generic transmission
  // fields refer to S11 too; they are not a two-port transmission measurement.
  let result : Json = {
    "input_text": text.to_json(),
    "metrics": metrics.to_json(),
  }
  println(result.stringify())
}

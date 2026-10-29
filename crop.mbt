///|
/// Keep original network records in a closed finite nonnegative Hz interval.
/// No interpolation or basis conversion; preserve reference/mode/information.
/// Returns an owned document; empty selections and actual noise data raise.
/// Noise cropping is not defined by this deterministic-file operation.
/// See docs/CROP-FREQUENCIES.md and scikit-rf's original-point crop workflow.
pub fn Document::crop(
  self : Document,
  start_hz : Double,
  end_hz : Double,
) -> Document raise {
  if !finite(start_hz) || !finite(end_hz) || start_hz < 0.0 || start_hz > end_hz {
    raise Failure("crop requires finite nonnegative ordered Hz bounds")
  }
  if !self.noise.is_empty() {
    raise Failure(
      "crop does not support noise data; retain the original document",
    )
  }
  let frequencies = []
  let matrices = []
  for i, f in self.data.frequencies {
    if f >= start_hz && f <= end_hz {
      frequencies.push(f)
      matrices.push(self.data.values[i])
    }
  }
  if frequencies.is_empty() {
    raise Failure("crop range contains no original network samples")
  }
  document(
    network(
      self.data.n,
      frequencies,
      matrices,
      self.data.reference,
      parameter=self.data.kind,
    ),
    noise_reference_ohms=self.noise_reference,
    mixed_mode_order=self.mixed,
    information=self.information,
  )
}

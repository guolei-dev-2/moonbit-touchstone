///|
/// Index refers to the supplied GT trace; the file CLI supplies the full trace.
/// None fields follow the canonical GT state, not a fabricated zero dB value.
pub(all) struct TransducerGainObservation {
  point : Int
  frequency_hz : Double
  gain : Double?
  gain_db : Double?
  state : String
} derive(ToJson)

///|
pub extend TransducerGainObservation with ToJson::{to_json}

///|
/// Sampled-only inclusive dB limits. Singular points are unknown; zero power
/// is negative-infinite dB; positive underflow/overflow retain finite dB.
/// Any known violation wins over coverage/unknown inconclusive conditions.
pub(all) struct TransducerGainBandReport {
  scope : String
  status : String
  start_hz : Double
  end_hz : Double
  minimum_db : Double?
  maximum_db : Double?
  sample_count : Int
  state_counts : Map[String, Int]
  below_minimum_count : Int
  above_maximum_count : Int
  range_covered : Bool
  start_sampled : Bool
  end_sampled : Bool
  lowest : TransducerGainObservation?
  highest : TransducerGainObservation?
  reasons : Array[String]
} derive(ToJson)

///|
pub extend TransducerGainBandReport with ToJson::{to_json}

///|
fn validate_gain_band_point(point : TransducerGainPoint) -> Unit raise {
  let valid = match (point.state, point.gain, point.gain_db) {
    ("finite", Some(g), Some(db)) => finite(g) && g > 0.0 && finite(db)
    ("zero", Some(g), None) => g == 0.0
    ("singular", None, None) => true
    ("overflow", None, Some(db)) => finite(db)
    ("underflow", Some(g), Some(db)) => g == 0.0 && finite(db)
    _ => false
  }
  if !valid {
    raise Failure("invalid canonical GT point state/fields")
  }
}

///|
fn gain_band_less(
  a : TransducerGainObservation,
  b : TransducerGainObservation,
) -> Bool {
  if b.state == "zero" {
    false
  } else if a.state == "zero" {
    true
  } else {
    a.gain_db.unwrap() < b.gain_db.unwrap()
  }
}

///|
/// Check original GT samples in a closed Hz interval. Bounds are finite,
/// inclusive, with no implicit tolerance/interpolation. Empty/uncovered or
/// singular selections are inconclusive unless a known value already fails.
/// Input must be a canonical trace (<=100000, ordered finite frequencies).
pub fn check_transducer_gain(
  points : Array[TransducerGainPoint],
  start_hz : Double,
  end_hz : Double,
  minimum_db? : Double,
  maximum_db? : Double,
) -> TransducerGainBandReport raise {
  if !finite(start_hz) || !finite(end_hz) || start_hz < 0.0 || end_hz < start_hz {
    raise Failure("gain band requires finite 0<=start_hz<=end_hz")
  }
  if minimum_db is None && maximum_db is None {
    raise Failure("gain check requires a dB bound")
  }
  if minimum_db is Some(v) && !finite(v) {
    raise Failure("gain minimum must be finite")
  }
  if maximum_db is Some(v) && !finite(v) {
    raise Failure("gain maximum must be finite")
  }
  if minimum_db is Some(lo) && maximum_db is Some(hi) && lo > hi {
    raise Failure("gain minimum exceeds maximum")
  }
  if points.length() > 100000 {
    raise Failure("gain trace exceeds 100000 points")
  }
  let counts : Map[String, Int] = Map([
    ("finite", 0),
    ("zero", 0),
    ("singular", 0),
    ("overflow", 0),
    ("underflow", 0),
  ])
  let mut samples = 0
  let mut below = 0
  let mut above = 0
  let mut start_sampled = false
  let mut end_sampled = false
  let mut lowest : TransducerGainObservation? = None
  let mut highest : TransducerGainObservation? = None
  for i, point in points {
    if !finite(point.frequency_hz) ||
      point.frequency_hz < 0.0 ||
      (i > 0 && point.frequency_hz <= points[i - 1].frequency_hz) {
      raise Failure(
        "gain frequencies must be finite nonnegative and strictly increasing",
      )
    }
    validate_gain_band_point(point)
    if point.frequency_hz < start_hz || point.frequency_hz > end_hz {
      continue
    }
    samples += 1
    counts[point.state] = counts.get(point.state).unwrap() + 1
    if point.frequency_hz == start_hz {
      start_sampled = true
    }
    if point.frequency_hz == end_hz {
      end_sampled = true
    }
    if point.state == "singular" {
      continue
    }
    let observation = {
      point: i,
      frequency_hz: point.frequency_hz,
      gain: point.gain,
      gain_db: point.gain_db,
      state: point.state,
    }
    match lowest {
      None => lowest = Some(observation)
      Some(old) =>
        if gain_band_less(observation, old) {
          lowest = Some(observation)
        }
    }
    match highest {
      None => highest = Some(observation)
      Some(old) =>
        if gain_band_less(old, observation) {
          highest = Some(observation)
        }
    }
    if minimum_db is Some(lo) &&
      (point.state == "zero" || point.gain_db.unwrap() < lo) {
      below += 1
    }
    if maximum_db is Some(hi) &&
      point.state != "zero" &&
      point.gain_db.unwrap() > hi {
      above += 1
    }
  }
  let covered = !points.is_empty() &&
    points[0].frequency_hz <= start_hz &&
    points[points.length() - 1].frequency_hz >= end_hz
  let singular = counts.get("singular").unwrap()
  let reasons = []
  if below > 0 {
    reasons.push("below_minimum")
  }
  if above > 0 {
    reasons.push("above_maximum")
  }
  if !covered {
    reasons.push("incomplete_range")
  }
  if samples == 0 {
    reasons.push("no_samples")
  }
  if singular > 0 {
    reasons.push("singular_samples")
  }
  let status = if below > 0 || above > 0 {
    "fail"
  } else if !covered || samples == 0 || singular > 0 {
    "inconclusive"
  } else {
    reasons.push("limits_met")
    "pass"
  }
  {
    scope: "sampled_points_only",
    status,
    start_hz,
    end_hz,
    minimum_db,
    maximum_db,
    sample_count: samples,
    state_counts: counts,
    below_minimum_count: below,
    above_maximum_count: above,
    range_covered: covered,
    start_sampled,
    end_sampled,
    lowest,
    highest,
    reasons,
  }
}

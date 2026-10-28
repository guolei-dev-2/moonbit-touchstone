///|
/// One ORIGINAL sampled estimate of -d(phase)/d(angular frequency), in seconds.
/// The aperture is the exact pair used by the existing group_delay estimator;
/// it may extend outside the selected report band. No new smoothing is applied.
pub struct GroupDelaySample {
  point : Int
  frequency_hz : Double
  delay_seconds : Double
  aperture_start_hz : Double
  aperture_end_hz : Double
  below_minimum : Bool
  above_maximum : Bool
  status : String
} derive(ToJson)

///|
pub extend GroupDelaySample with ToJson::{to_json}

///|
/// Closed-band limits on the existing sampled group-delay estimates. Bounds
/// are inclusive SI seconds, including negative values and explicit zero.
/// fail takes precedence over missing range coverage; empty bands cannot pass.
pub struct GroupDelayBandReport {
  scope : String
  estimator : String
  status : String
  start_hz : Double
  end_hz : Double
  input : Int
  output : Int
  reference_ohms : Array[Double]
  minimum_seconds : Double?
  maximum_seconds : Double?
  sample_count : Int
  failed_count : Int
  below_minimum_count : Int
  above_maximum_count : Int
  range_covered : Bool
  start_sampled : Bool
  end_sampled : Bool
  lowest : GroupDelaySample?
  highest : GroupDelaySample?
  samples : Array[GroupDelaySample]
}

///|
pub impl ToJson for GroupDelayBandReport with fn to_json(self) {
  {
    "kind": "group_delay_band_report",
    "scope": self.scope.to_json(),
    "estimator": self.estimator.to_json(),
    "status": self.status.to_json(),
    "start_hz": self.start_hz.to_json(),
    "end_hz": self.end_hz.to_json(),
    "input": self.input.to_json(),
    "output": self.output.to_json(),
    "reference_ohms": self.reference_ohms.to_json(),
    "minimum_seconds": nullable_number(self.minimum_seconds),
    "maximum_seconds": nullable_number(self.maximum_seconds),
    "sample_count": self.sample_count.to_json(),
    "failed_count": self.failed_count.to_json(),
    "below_minimum_count": self.below_minimum_count.to_json(),
    "above_maximum_count": self.above_maximum_count.to_json(),
    "range_covered": self.range_covered.to_json(),
    "start_sampled": self.start_sampled.to_json(),
    "end_sampled": self.end_sampled.to_json(),
    "lowest": match self.lowest {
      Some(sample) => sample.to_json()
      None => null
    },
    "highest": match self.highest {
      Some(sample) => sample.to_json()
      None => null
    },
    "samples": self.samples.to_json(),
  }
}

///|
pub extend GroupDelayBandReport with ToJson::{to_json}

///|
/// Check existing group_delay values in a closed Hz band. Compute on the FULL
/// original trace before selecting points, retaining endpoint/centered secant
/// stencils and nearest-neighbor phase unwrap. All original selected S elements
/// must be nonzero and at least two frequencies are required, even if a zero
/// lies outside the report band. Bounds compare exactly, without epsilon.
/// This is sampled acceptance, not continuous-band or aperture-independent
/// certification. See docs/GROUP-DELAY-CHECK.md and the existing estimator.
pub fn Network::check_group_delay(
  self : Network,
  start_hz : Double,
  end_hz : Double,
  input~ : Int,
  output~ : Int,
  minimum_seconds? : Double,
  maximum_seconds? : Double,
) -> GroupDelayBandReport raise {
  validate_band_domain(start_hz, end_hz, input, output)
  check_ports(self.n, output, input)
  if minimum_seconds is None && maximum_seconds is None {
    raise Failure(
      "group delay check requires a minimum_seconds or maximum_seconds",
    )
  }
  if minimum_seconds is Some(value) && !finite(value) {
    raise Failure("minimum_seconds must be finite")
  }
  if maximum_seconds is Some(value) && !finite(value) {
    raise Failure("maximum_seconds must be finite")
  }
  if minimum_seconds is Some(lo) && maximum_seconds is Some(hi) && lo > hi {
    raise Failure("minimum_seconds exceeds maximum_seconds")
  }
  let delays = self.group_delay(output, input)
  let frequencies = self.frequency_hz()
  let samples : Array[GroupDelaySample] = []
  let mut lowest : GroupDelaySample? = None
  let mut highest : GroupDelaySample? = None
  let mut below_count = 0
  let mut above_count = 0
  let mut start_sampled = false
  let mut end_sampled = false
  for i, frequency in frequencies {
    if frequency < start_hz || frequency > end_hz {
      continue
    }
    let value = delays[i]
    let below = minimum_seconds is Some(lo) && value < lo
    let above = maximum_seconds is Some(hi) && value > hi
    if below {
      below_count += 1
    }
    if above {
      above_count += 1
    }
    if frequency == start_hz {
      start_sampled = true
    }
    if frequency == end_hz {
      end_sampled = true
    }
    let sample : GroupDelaySample = {
      point: i,
      frequency_hz: frequency,
      delay_seconds: value,
      aperture_start_hz: frequencies[(i - 1).max(0)],
      aperture_end_hz: frequencies[(i + 1).min(frequencies.length() - 1)],
      below_minimum: below,
      above_maximum: above,
      status: if below || above {
        "fail"
      } else {
        "pass"
      },
    }
    match lowest {
      None => lowest = Some(sample)
      Some(old) => if value < old.delay_seconds { lowest = Some(sample) }
    }
    match highest {
      None => highest = Some(sample)
      Some(old) => if value > old.delay_seconds { highest = Some(sample) }
    }
    samples.push(sample)
  }
  let covered = frequencies[0] <= start_hz &&
    frequencies[frequencies.length() - 1] >= end_hz
  let failed_count = below_count + above_count
  {
    scope: "sampled_points_only",
    estimator: "endpoint_or_centered_secant",
    status: if failed_count > 0 {
      "fail"
    } else if samples.is_empty() || !covered {
      "inconclusive"
    } else {
      "pass"
    },
    start_hz,
    end_hz,
    input,
    output,
    reference_ohms: self.reference_ohms(),
    minimum_seconds,
    maximum_seconds,
    sample_count: samples.length(),
    failed_count,
    below_minimum_count: below_count,
    above_maximum_count: above_count,
    range_covered: covered,
    start_sampled,
    end_sampled,
    lowest,
    highest,
    samples,
  }
}

///|
/// An original NETWORK-grid sample of source-dependent noise figure, in dB.
pub struct NoiseFigureSample {
  point : Int
  frequency_hz : Double
  figure_db : Double
  above_maximum : Bool
  status : String
} derive(ToJson)

///|
pub extend NoiseFigureSample with ToJson::{to_json}

///|
/// Sampled upper-limit acceptance with source and independent noise-reference
/// conditions. Range coverage describes the stored network extent only.
pub struct NoiseFigureBandReport {
  scope : String
  figure_units : String
  status : String
  start_hz : Double
  end_hz : Double
  maximum_db : Double
  source_mode : String
  source : Complex
  source_units : String
  network_reference_ohms : Array[Double]
  noise_reference_ohms : Double
  noise_records : Int
  available_start_hz : Double
  available_end_hz : Double
  range_covered : Bool
  start_sampled : Bool
  end_sampled : Bool
  sample_count : Int
  failed_count : Int
  highest : NoiseFigureSample?
  samples : Array[NoiseFigureSample]
}

///|
pub impl ToJson for NoiseFigureBandReport with fn to_json(self) {
  {
    "kind": "noise_figure_band_report",
    "scope": self.scope.to_json(),
    "figure_units": self.figure_units.to_json(),
    "status": self.status.to_json(),
    "start_hz": self.start_hz.to_json(),
    "end_hz": self.end_hz.to_json(),
    "maximum_db": self.maximum_db.to_json(),
    "source_mode": self.source_mode.to_json(),
    "source": self.source.to_json(),
    "source_units": self.source_units.to_json(),
    "network_reference_ohms": self.network_reference_ohms.to_json(),
    "noise_reference_ohms": self.noise_reference_ohms.to_json(),
    "noise_records": self.noise_records.to_json(),
    "available_start_hz": self.available_start_hz.to_json(),
    "available_end_hz": self.available_end_hz.to_json(),
    "range_covered": self.range_covered.to_json(),
    "start_sampled": self.start_sampled.to_json(),
    "end_sampled": self.end_sampled.to_json(),
    "sample_count": self.sample_count.to_json(),
    "failed_count": self.failed_count.to_json(),
    "highest": match self.highest {
      Some(sample) => sample.to_json()
      None => null
    },
    "samples": self.samples.to_json(),
  }
}

///|
pub extend NoiseFigureBandReport with ToJson::{to_json}

///|
/// Apply one inclusive upper dB limit to original samples in a closed Hz band.
/// Gamma is relative to noise_reference_ohms; impedance=true takes physical
/// ohm directly. Reuse the existing Haus-Adler noise methods on the FULL grid
/// before selecting, retaining covariance, source and interpolation errors.
/// No endpoint interpolation or continuous-band/uncertainty certification.
/// Known failures win over incomplete extent coverage; empty bands cannot pass.
/// Ties retain the first original maximum. See docs/NOISE-CHECK.md and the
/// Keysight N8201A NF Guide p154 for the frequency/limit receiver workflow.
pub fn Document::check_noise_figure(
  self : Document,
  start_hz : Double,
  end_hz : Double,
  source : Complex,
  maximum_db~ : Double,
  impedance? : Bool = false,
) -> NoiseFigureBandReport raise {
  validate_band_domain(start_hz, end_hz, 0, 1)
  if !finite(maximum_db) {
    raise Failure("noise maximum_db must be finite")
  }
  if !self.mixed.is_empty() {
    raise Failure("noise check requires a single-ended document")
  }
  let figures = if impedance {
    self.noise_figure_impedance(source)
  } else {
    self.noise_figure(source)
  }
  let frequencies = self.data.frequency_hz()
  let samples : Array[NoiseFigureSample] = []
  let mut highest : NoiseFigureSample? = None
  let mut failed_count = 0
  let mut start_sampled = false
  let mut end_sampled = false
  for i, frequency in frequencies {
    if frequency < start_hz || frequency > end_hz {
      continue
    }
    let value = figures[i]
    let above = value > maximum_db
    if above {
      failed_count += 1
    }
    if frequency == start_hz {
      start_sampled = true
    }
    if frequency == end_hz {
      end_sampled = true
    }
    let sample : NoiseFigureSample = {
      point: i,
      frequency_hz: frequency,
      figure_db: value,
      above_maximum: above,
      status: if above {
        "fail"
      } else {
        "pass"
      },
    }
    match highest {
      None => highest = Some(sample)
      Some(old) => if value > old.figure_db { highest = Some(sample) }
    }
    samples.push(sample)
  }
  let first = frequencies[0]
  let last = frequencies[frequencies.length() - 1]
  let covered = first <= start_hz && last >= end_hz
  {
    scope: "sampled_points_only",
    figure_units: "dB",
    status: if failed_count > 0 {
      "fail"
    } else if samples.is_empty() || !covered {
      "inconclusive"
    } else {
      "pass"
    },
    start_hz,
    end_hz,
    maximum_db,
    source_mode: if impedance {
      "impedance"
    } else {
      "gamma"
    },
    source,
    source_units: if impedance {
      "ohm"
    } else {
      "dimensionless"
    },
    network_reference_ohms: self.data.reference_ohms(),
    noise_reference_ohms: self.noise_reference,
    noise_records: self.noise.length(),
    available_start_hz: first,
    available_end_hz: last,
    range_covered: covered,
    start_sampled,
    end_sampled,
    sample_count: samples.length(),
    failed_count,
    highest,
    samples,
  }
}

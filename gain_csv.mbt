///|
fn gain_csv_number(value : Double?) -> String {
  match value {
    Some(value) => value.to_string()
    None => ""
  }
}

///|
/// Export every original sample in the closed Hz band, with per-sample limits
/// and the global sampled verdict. Reuse the canonical trace/bounds contract;
/// a header-only table does not imply pass. Empty dB means zero or singular
/// according to state, while positive overflow/underflow retain finite dB.
/// All cells are finite numbers, booleans, or validated fixed identifiers;
/// arbitrary user text is never placed into CSV cells. LF, comma, no BOM.
pub fn transducer_gain_samples_csv(
  points : Array[TransducerGainPoint],
  start_hz : Double,
  end_hz : Double,
  minimum_db? : Double,
  maximum_db? : Double,
) -> String raise {
  let report = check_transducer_gain(
    points,
    start_hz,
    end_hz,
    minimum_db?,
    maximum_db?,
  )
  let out = StringBuilder()
  out.write_string(
    "point,frequency_hz,gain,gain_db,state,start_hz,end_hz,minimum_db,maximum_db,below_minimum,above_maximum,sample_status,report_status,range_covered\n",
  )
  let lower = gain_csv_number(minimum_db)
  let upper = gain_csv_number(maximum_db)
  for i, point in points {
    if point.frequency_hz < start_hz || point.frequency_hz > end_hz {
      continue
    }
    let (below, above, status) = if point.state == "singular" {
      ("", "", "unknown")
    } else {
      let below = minimum_db is Some(lo) &&
        (point.state == "zero" || point.gain_db.unwrap() < lo)
      let above = maximum_db is Some(hi) &&
        point.state != "zero" &&
        point.gain_db.unwrap() > hi
      (
        below.to_string(),
        above.to_string(),
        if below || above {
          "fail"
        } else {
          "pass"
        },
      )
    }
    let gain = gain_csv_number(point.gain)
    let db = gain_csv_number(point.gain_db)
    out.write_string(
      "\{i},\{point.frequency_hz},\{gain},\{db},\{point.state},\{start_hz},\{end_hz},\{lower},\{upper},\{below},\{above},\{status},\{report.status},\{report.range_covered}\n",
    )
  }
  out.to_string()
}

///|
fn csv_point(
  hz : Double,
  gain : Double?,
  db : Double?,
  state : String,
) -> @touchstone.TransducerGainPoint {
  { frequency_hz: hz, gain, gain_db: db, state, }
}

///|
fn csv_header() -> String {
  "point,frequency_hz,gain,gain_db,state,start_hz,end_hz,minimum_db,maximum_db,below_minimum,above_maximum,sample_status,report_status,range_covered\n"
}

///|
test "GT CSV fixed five-state review truth table" {
  let points = [
    csv_point(1.0, Some(1.0), Some(0.0), "finite"),
    csv_point(2.0, Some(0.0), None, "zero"),
    csv_point(3.0, Some(0.0), Some(-4000.0), "underflow"),
    csv_point(4.0, None, Some(4000.0), "overflow"),
    csv_point(5.0, None, None, "singular"),
  ]
  assert_eq(
    @touchstone.transducer_gain_samples_csv(
      points,
      1.0,
      5.0,
      minimum_db=-3000.0,
      maximum_db=3000.0,
    ),
    csv_header() +
    "0,1,1,0,finite,1,5,-3000,3000,false,false,pass,fail,true\n" +
    "1,2,0,,zero,1,5,-3000,3000,true,false,fail,fail,true\n" +
    "2,3,0,-4000,underflow,1,5,-3000,3000,true,false,fail,fail,true\n" +
    "3,4,,4000,overflow,1,5,-3000,3000,false,true,fail,fail,true\n" +
    "4,5,,,singular,1,5,-3000,3000,,,unknown,fail,true\n",
  )
}

///|
test "GT CSV keeps full-trace indices and inclusive zero boundaries" {
  let points = [
    csv_point(1.0, Some(0.1), Some(-10.0), "finite"),
    csv_point(2.0, Some(1.0), Some(0.0), "finite"),
    csv_point(3.0, Some(10.0), Some(10.0), "finite"),
  ]
  assert_eq(
    @touchstone.transducer_gain_samples_csv(
      points,
      2.0,
      2.0,
      minimum_db=0.0,
      maximum_db=0.0,
    ),
    csv_header() + "1,2,1,0,finite,2,2,0,0,false,false,pass,pass,true\n",
  )
}

///|
test "GT CSV one-bound zero and unknown remain distinct" {
  let points = [
    csv_point(1.0, Some(0.0), None, "zero"),
    csv_point(2.0, None, None, "singular"),
  ]
  assert_eq(
    @touchstone.transducer_gain_samples_csv(points, 1.0, 2.0, maximum_db=0.0),
    csv_header() +
    "0,1,0,,zero,1,2,,0,false,false,pass,inconclusive,true\n" +
    "1,2,,,singular,1,2,,0,,,unknown,inconclusive,true\n",
  )
  assert_eq(
    @touchstone.transducer_gain_samples_csv(points, 1.0, 1.0, minimum_db=0.0),
    csv_header() + "0,1,0,,zero,1,1,0,,true,false,fail,fail,true\n",
  )
}

///|
test "GT CSV local passing rows do not conceal incomplete coverage" {
  let points = [csv_point(2.0, Some(1.0), Some(0.0), "finite")]
  assert_eq(
    @touchstone.transducer_gain_samples_csv(points, 1.0, 3.0, minimum_db=0.0),
    csv_header() + "0,2,1,0,finite,1,3,0,,false,false,pass,inconclusive,false\n",
  )
  assert_eq(
    @touchstone.transducer_gain_samples_csv(points, 0.0, 1.0, maximum_db=0.0),
    csv_header(),
  )
  assert_eq(
    @touchstone.transducer_gain_samples_csv([], 0.0, 1.0, maximum_db=0.0),
    csv_header(),
  )
}

///|
test "GT CSV validates all points before selecting rows" {
  let good = csv_point(1.0, Some(1.0), Some(0.0), "finite")
  let invalid = [
    csv_point(2.0, Some(0.0), None, "finite"),
    csv_point(2.0, Some(0.0), Some(1.0), "zero"),
    csv_point(2.0, None, None, "untrusted,text"),
    csv_point(0.0, Some(1.0), Some(0.0), "finite"),
  ]
  for bad in invalid {
    let mut rejected = false
    ignore(
      @touchstone.transducer_gain_samples_csv(
        [good, bad],
        1.0,
        1.0,
        maximum_db=0.0,
      ),
    ) catch {
      _ => rejected = true
    }
    assert_true(rejected)
  }
}

///|
test "GT CSV bound errors produce no fabricated table" {
  let points = [csv_point(1.0, Some(1.0), Some(0.0), "finite")]
  let cases = [
    (1.0, 0.0, Some(0.0), None),
    (0.0, 1.0, None, None),
    (0.0, 1.0, Some(1.0), Some(0.0)),
  ]
  for (start, end, lo, hi) in cases {
    let mut rejected = false
    ignore(
      @touchstone.transducer_gain_samples_csv(
        points,
        start,
        end,
        minimum_db?=lo,
        maximum_db?=hi,
      ),
    ) catch {
      _ => rejected = true
    }
    assert_true(rejected)
  }
}

///|
test "GT CSV full capacity keeps every row and rejects capacity plus one" {
  let points = Array::makei(100000, i => {
    csv_point(i.to_double(), Some(1.0), Some(0.0), "finite")
  })
  let text = @touchstone.transducer_gain_samples_csv(
    points,
    0.0,
    99999.0,
    maximum_db=0.0,
  )
  let mut lines = 0
  for ch in text.iter() {
    if ch == '\n' {
      lines += 1
    }
  }
  assert_eq(lines, 100001)
  assert_true(
    text.contains(
      "99999,99999,1,0,finite,0,99999,,0,false,false,pass,pass,true\n",
    ),
  )
  points.push(csv_point(100000.0, Some(1.0), Some(0.0), "finite"))
  let mut rejected = false
  ignore(
    @touchstone.transducer_gain_samples_csv(
      points,
      0.0,
      100000.0,
      maximum_db=0.0,
    ),
  ) catch {
    _ => rejected = true
  }
  assert_true(rejected)
}

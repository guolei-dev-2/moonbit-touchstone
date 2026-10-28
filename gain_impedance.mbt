///|
fn gain_negate(value : GainScaled) -> GainScaled {
  { z: value.z.scale(-1.0), exponent: value.exponent, }
}

///|
// TwoSum for real scaled values. A gap>60 bits cannot change the larger
// rounded mantissa, so retain the smaller value as the exact residual instead
// of shifting it into underflow. Otherwise all aligned operands are normal.
fn gain_impedance_real_parts(
  a : GainScaled,
  b : GainScaled,
) -> (GainScaled, GainScaled) {
  let zero = gain_scaled(complex(0.0))
  if a.z.re == 0.0 {
    return (b, zero)
  }
  if b.z.re == 0.0 {
    return (a, zero)
  }
  if a.exponent - b.exponent > 60 {
    return (a, b)
  }
  if b.exponent - a.exponent > 60 {
    return (b, a)
  }
  let e = a.exponent.max(b.exponent)
  let (sum, error) = gain_two_sum(
    @math.scalbn(a.z.re, a.exponent - e),
    @math.scalbn(b.z.re, b.exponent - e),
  )
  (
    gain_scaled(complex(sum), exponent=e),
    gain_scaled(complex(error), exponent=e),
  )
}

///|
fn gain_impedance_component_sum(
  terms : Array[GainScaled],
  imaginary : Bool,
) -> GainScaled {
  let mut expansion : Array[GainScaled] = []
  for term in terms {
    let mut sum = gain_scaled(
      complex(if imaginary { term.z.im } else { term.z.re }),
      exponent=term.exponent,
    )
    let next = []
    for component in expansion {
      let (value, error) = gain_impedance_real_parts(sum, component)
      if error.z.re != 0.0 {
        next.push(error)
      }
      sum = value
    }
    if sum.z.re != 0.0 {
      next.push(sum)
    }
    expansion = next
  }
  // The expansion's large cancellations have finished; round its remaining
  // nonoverlapping components only now, before the final magnitude calculation.
  gain_sum(expansion)
}

///|
fn gain_impedance_sum(terms : Array[GainScaled]) -> GainScaled {
  let re = gain_impedance_component_sum(terms, false)
  let im = gain_impedance_component_sum(terms, true)
  if im.z.re == 0.0 {
    return re
  }
  if re.z.re == 0.0 {
    return { z: complex(0.0, im=im.z.re), exponent: im.exponent, }
  }
  let e = re.exponent.max(im.exponent)
  gain_scaled(
    complex(
      @math.scalbn(re.z.re, re.exponent - e),
      im=@math.scalbn(im.z.re, im.exponent - e),
    ),
    exponent=e,
  )
}

///|
/// Transducer POWER gain for physical source/load impedances in ohm. Source
/// Re(Z)>0, load Re(Z)>=0; both finite. Port0 is source, port1 load. Network
/// references remain fixed positive real. Result/state semantics match the
/// Gamma method; physical input avoids rounding a positive resistance to |G|=1.
/// Qucs eq1.49-1.57, with G=(Z-R)/(Z+R): homogeneous H and power factors
/// are expanded in Z components before summation, not evaluated via rounded G.
pub fn Network::transducer_gain_impedance(
  self : Network,
  source : Complex,
  load : Complex,
) -> Array[TransducerGainPoint] raise {
  if self.n != 2 {
    raise Failure("impedance transducer gain requires a two-port")
  }
  ignore(checked(source))
  ignore(checked(load))
  if source.re <= 0.0 || load.re < 0.0 {
    raise Failure("impedance gain requires Re(source)>0 and Re(load)>=0 ohm")
  }
  let rs = gain_scaled(complex(self.reference[0]))
  let rl = gain_scaled(complex(self.reference[1]))
  let sr = gain_scaled(complex(source.re))
  let si = gain_scaled(complex(0.0, im=source.im))
  let lr = gain_scaled(complex(load.re))
  let li = gain_scaled(complex(0.0, im=load.im))
  // Each tuple is a physical product and the signs of its S11,S22,det(S)
  // contributions. Do not pre-round A/B/C/E coefficients before cancellation.
  let products = [
    (gain_product(sr, lr), true, true, false),
    (gain_product(sr, li), true, true, false),
    (gain_product(si, lr), true, true, false),
    (gain_product(si, li), true, true, false),
    (gain_product(sr, rl), true, false, true),
    (gain_product(si, rl), true, false, true),
    (gain_product(rs, lr), false, true, true),
    (gain_product(rs, li), false, true, true),
    (gain_product(rs, rl), false, false, false),
  ]
  let available = gain_product(
    gain_product(gain_scaled(complex(16.0)), gain_product(rs, rl)),
    gain_product(sr, lr),
  )
  let one = gain_scaled(complex(1.0))
  let s = self.convert("S")
  Array::makei(s.values.length(), i => {
    let m = s.values[i].map(v => gain_scaled(v))
    let delta = gain_difference(
      gain_product(m[0], m[3]),
      gain_product(m[1], m[2]),
    )
    // H=A*ZsZl+B*ZsRl+C*RsZl+E*RsRl. Keep real and imaginary
    // terminal components AND coefficient contributions separate until large
    // terms cancel. This retains matched-port constants even for huge S11/S22.
    let terms = []
    for (physical, negative11, negative22, negative_delta) in products {
      terms.push(gain_product(one, physical))
      let term11 = gain_product(m[0], physical)
      let term22 = gain_product(m[3], physical)
      let term_delta = gain_product(delta, physical)
      terms.push(if negative11 { gain_negate(term11) } else { term11 })
      terms.push(if negative22 { gain_negate(term22) } else { term22 })
      terms.push(
        if negative_delta {
          gain_negate(term_delta)
        } else {
          term_delta
        },
      )
    }
    let h = gain_impedance_sum(terms)
    let (gain, gain_db, state) = if h.z.re == 0.0 && h.z.im == 0.0 {
      (None, None, "singular")
    } else if (m[2].z.re == 0.0 && m[2].z.im == 0.0) || load.re == 0.0 {
      (Some(0.0), None, "zero")
    } else {
      let norm = (z : Complex) => z.re * z.re + z.im * z.im
      let coefficient = norm(m[2].z) / norm(h.z) * available.z.re
      let exponent = 2 * (m[2].exponent - h.exponent) + available.exponent
      let power = @math.scalbn(coefficient, exponent)
      let db = 10.0 * @math.log10(coefficient) +
        10.0 * exponent.to_double() * @math.log10(2.0)
      if power.is_inf() {
        (None, Some(db), "overflow")
      } else if power == 0.0 {
        (Some(0.0), Some(db), "underflow")
      } else {
        (Some(power), Some(db), "finite")
      }
    }
    { frequency_hz: s.frequencies[i], gain, gain_db, state, }
  })
}

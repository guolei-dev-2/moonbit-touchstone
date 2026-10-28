///|
// IBIS Touchstone 2.1, pp.20-23 and Appendix A: Vm=P*V, Im=Q*I.
// Differential voltage/current are Vp-Vq and (Ip-Iq)/2; common are
// (Vp+Vq)/2 and Ip+Iq. Descriptors reference original single-ended ports.
fn mode_transforms(
  n : Int,
  order : Array[String],
  refs : Array[Double],
) -> (Array[Complex], Array[Complex], Array[Double]) raise {
  let dummy = network(n, [0.0], [identity(n)], refs)
  validate_mixed(dummy, order)
  if order.is_empty() {
    raise Failure("mode order must contain one descriptor per port")
  }
  let p = Array::make(n * n, complex(0.0))
  let q = Array::make(n * n, complex(0.0))
  let effective = []
  for row, mode in order {
    let tail = mode[1:].to_owned()
    if mode[0] == 'S' {
      let a = port_number(tail, n)
      p[row * n + a] = complex(1.0)
      q[row * n + a] = complex(1.0)
      effective.push(refs[a])
    } else {
      let pair = tail.split(",").map(x => x.to_owned()).to_array()
      let a = port_number(pair[0], n)
      let b = port_number(pair[1], n)
      let d = mode[0] == 'D'
      p[row * n + a] = complex(if d { 1.0 } else { 0.5 })
      p[row * n + b] = complex(if d { -1.0 } else { 0.5 })
      q[row * n + a] = complex(if d { 0.5 } else { 1.0 })
      q[row * n + b] = complex(if d { -0.5 } else { 1.0 })
      effective.push(refs[a] * (if d { 2.0 } else { 0.5 }))
    }
  }
  (p, q, effective)
}

///|
/// Return matrices in descriptor order at effective modal references. Accepts
/// S/Y/Z and any disjoint ordered pairs, plus unpaired S ports. Pair references
/// must be equal, as required by Touchstone 2.1. No port count/parity shortcut.
pub fn Network::mixed_mode(
  self : Network,
  order : Array[String],
) -> Network raise {
  if !(self.kind == "S" || self.kind == "Y" || self.kind == "Z") {
    raise Failure("mixed mode requires S/Y/Z")
  }
  let modes = order.map(x => x.to_upper())
  let (p, q, refs) = mode_transforms(self.n, modes, self.reference)
  let pinv = invert_matrix(self.n, p)
  let qinv = invert_matrix(self.n, q)
  let values = self.values.map(m => {
    let (a, b) = constraints(self.n, self.kind, m, self.reference)
    solve_representation(
      self.n,
      self.kind,
      product(self.n, a, pinv),
      product(self.n, b, qinv),
      refs,
    )
  })
  network(self.n, self.frequencies, values, refs, parameter=self.kind)
}

///|
/// Invert a modal network at effective modal references. The original real
/// single-ended references are explicit; their consistency is checked.
pub fn Network::single_ended(
  self : Network,
  order : Array[String],
  single_reference_ohms : Array[Double],
) -> Network raise {
  if !(self.kind == "S" || self.kind == "Y" || self.kind == "Z") {
    raise Failure("mixed mode requires S/Y/Z")
  }
  let (p, q, refs) = mode_transforms(
    self.n,
    order.map(x => x.to_upper()),
    single_reference_ohms,
  )
  if refs != self.reference {
    raise Failure("modal references do not match original port references")
  }
  let values = self.values.map(m => {
    let (a, b) = constraints(self.n, self.kind, m, self.reference)
    solve_representation(
      self.n,
      self.kind,
      product(self.n, a, p),
      product(self.n, b, q),
      single_reference_ohms,
    )
  })
  network(
    self.n,
    self.frequencies,
    values,
    single_reference_ohms,
    parameter=self.kind,
  )
}

///|
/// Build a serializable mixed-mode document. Pair indices are zero based;
/// result order is all D pairs, all C pairs, then unpaired S ports.
pub fn Network::to_mixed_mode(
  self : Network,
  pairs : Array[(Int, Int)],
) -> Document raise {
  let used = Array::make(self.n, false)
  let order = []
  for (a, b) in pairs {
    if a < 0 ||
      b < 0 ||
      a >= self.n ||
      b >= self.n ||
      a == b ||
      used[a] ||
      used[b] {
      raise Failure("invalid or overlapping differential pairs")
    }
    used[a] = true
    used[b] = true
    order.push("D\{a+1},\{b+1}")
  }
  for (a, b) in pairs {
    order.push("C\{a+1},\{b+1}")
  }
  for a in 0..<self.n {
    if !used[a] {
      order.push("S\{a+1}")
    }
  }
  let modal = self.mixed_mode(order)
  // File [Reference] describes original ports, not the effective modal Z0.
  document(
    network(
      self.n,
      self.frequencies,
      modal.values,
      self.reference,
      parameter=self.kind,
    ),
    mixed_mode_order=order,
  )
}

///|
/// Raw descriptor-ordered matrices with the effective D=2Z0 / C=Z0/2
/// impedances. This is suitable for RF operations on modal ports.
pub fn Document::modal_network(self : Document) -> Network raise {
  if self.mixed.is_empty() {
    return self.data
  }
  let (_, _, refs) = mode_transforms(
    self.data.n,
    self.mixed,
    self.data.reference,
  )
  network(
    self.data.n,
    self.data.frequencies,
    self.data.values,
    refs,
    parameter=self.data.kind,
  )
}

///|
/// Restore original single-ended port order from a mixed-mode file.
pub fn Document::single_ended_network(self : Document) -> Network raise {
  if self.mixed.is_empty() {
    return self.data
  }
  self.modal_network().single_ended(self.mixed, self.data.reference)
}

///|
pub(all) struct ModalMetric {
  frequency_hz : Double
  sdd : Complex
  sdc : Complex
  scd : Complex
  scc : Complex
  differential_insertion_loss_db : Double?
  differential_return_loss_db : Double?
  dc_conversion_loss_db : Double?
  cd_conversion_loss_db : Double?
  cmrr_db : Double?
  cmrr_state : String
  cmrr_definition : String
} derive(ToJson)

///|
pub extend ModalMetric with ToJson::{to_json}

///|
fn modal_log_magnitude(z : Complex) -> Double? {
  let m = z.magnitude()
  if m == 0.0 {
    None
  } else if finite(m) {
    Some(@math.log10(m))
  } else {
    // Finite components can have an unrepresentable linear magnitude while
    // their dB loss and CMRR remain finite. Scale only this overflow path so
    // the existing finite-magnitude results keep their exact computation.
    let scale = z.re.abs().max(z.im.abs())
    let re = z.re / scale
    let im = z.im / scale
    Some(@math.log10(scale) + 0.5 * @math.log10(re * re + im * im))
  }
}

///|
fn loss_db(z : Complex) -> Double? {
  match modal_log_magnitude(z) {
    Some(value) => Some(-20.0 * value)
    None => None
  }
}

///|
/// Pair numbers are zero-based positions among D descriptors.
/// cmrr="balanced" uses 20log10(|Sdd/Scc|), the balanced-to-balanced VNA
/// definition (Keysight Balanced Measurements). "input" uses Sdd/Sdc for
/// common input rejection at the differential output; "output" uses Sdd/Scd
/// for output balance under differential drive. These are power-wave ratios,
/// not voltage gains. None losses denote +infinity; CMRR has an explicit state.
pub fn Document::mixed_mode_metrics(
  self : Document,
  output_pair : Int,
  input_pair : Int,
  cmrr? : String = "balanced",
) -> Array[ModalMetric] raise {
  if !["balanced", "input", "output"].contains(cmrr) {
    raise Failure("CMRR definition must be balanced, input, or output")
  }
  let ds = []
  let cs = []
  for i, m in self.mixed {
    if m[0] == 'D' {
      ds.push(i)
      let name = "C" + m[1:].to_owned()
      let mut c = -1
      for j, v in self.mixed {
        if v == name {
          c = j
        }
      }
      cs.push(c)
    }
  }
  if output_pair < 0 ||
    input_pair < 0 ||
    output_pair >= ds.length() ||
    input_pair >= ds.length() {
    raise Failure("mixed-mode pair index out of range")
  }
  let s = self.modal_network().convert("S")
  let d = ds[output_pair]
  let c = cs[output_pair]
  let di = ds[input_pair]
  let ci = cs[input_pair]
  Array::makei(s.values.length(), i => {
    let m = s.values[i]
    let dd = m[d * s.n + di]
    let dc = m[d * s.n + ci]
    let cd = m[c * s.n + di]
    let cc = m[c * s.n + ci]
    let a = modal_log_magnitude(dd)
    let b = modal_log_magnitude(
      if cmrr == "balanced" {
        cc
      } else if cmrr == "input" {
        dc
      } else {
        cd
      },
    )
    {
      frequency_hz: s.frequencies[i],
      sdd: dd,
      sdc: dc,
      scd: cd,
      scc: cc,
      differential_insertion_loss_db: loss_db(dd),
      differential_return_loss_db: loss_db(m[di * s.n + di]),
      dc_conversion_loss_db: loss_db(dc),
      cd_conversion_loss_db: loss_db(cd),
      cmrr_db: match (a, b) {
        (Some(a), Some(b)) => Some(20.0 * (a - b))
        _ => None
      },
      cmrr_state: match (a, b) {
        (None, None) => "undefined"
        (Some(_), None) => "positive_infinity"
        (None, Some(_)) => "negative_infinity"
        (Some(_), Some(_)) => "finite"
      },
      cmrr_definition: cmrr,
    }
  })
}

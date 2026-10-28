///|
fn dagger(n : Int, m : Array[Complex]) -> Array[Complex] {
  Array::makei(n * n, k => m[k % n * n + k / n].conjugate())
}

///|
fn congruence(m : Array[Complex], c : Array[Complex]) -> Array[Complex] raise {
  product(2, product(2, m, c), dagger(2, m))
}

///|
// A covariance must be positive semidefinite, not merely produce positive
// Rn/Fmin. Normalize voltage/current units by Zref before a relative test;
// otherwise an absolute ohm/siemens tolerance changes with the reference.
fn validate_noise_covariance(
  c : Array[Complex],
  reference : Double,
) -> Unit raise {
  let a = c[0].re / reference
  let d = c[3].re * reference
  let b = c[1].magnitude()
  if !finite(a) || !finite(d) || !finite(b) {
    raise Failure("nonfinite noise covariance")
  }
  let scale = a.abs().max(d.abs()).max(b)
  if scale == 0.0 {
    return
  }
  let an = a / scale
  let dn = d / scale
  let bn = b / scale
  if an < -1.0e-11 || dn < -1.0e-11 || an * dn - bn * bn < -1.0e-11 {
    raise Failure("noise covariance is not positive semidefinite")
  }
}

///|
// Haus-Adler chain-voltage/current noise covariance normalized by 4*kB*T0.
// Thus N00 has ohm units and equals Rn; off diagonal is dimensionless,
// N11 siemens. This is the same convention as scikit-rf Network.noise/(4kT).
// References: scikit-rf Network.set_noise_a/nf/y_opt; Haus et al., IRE 1960.
fn noise_a(point : NoisePoint, reference : Double) -> Array[Complex] raise {
  let g = point.gamma_opt
  let y = complex(1.0).sub(g).divide(complex(1.0).add(g)).scale(1.0 / reference)
  let f = @math.pow(10.0, point.minimum_figure_db / 10.0)
  let cross = complex((f - 1.0) / 2.0).sub(
    y.conjugate().scale(point.resistance_ohms),
  )
  let covariance = [
    complex(point.resistance_ohms),
    checked(cross),
    cross.conjugate(),
    checked(complex(y.magnitude() * y.magnitude() * point.resistance_ohms)),
  ]
  validate_noise_covariance(covariance, reference)
  covariance
}

///|
fn noise_point(
  f : Double,
  c : Array[Complex],
  reference : Double,
) -> NoisePoint raise {
  validate_noise_covariance(c, reference)
  let rn = c[0].re
  // A dimensional absolute floor erases legitimate low-noise models and
  // changes meaning with impedance units. Only exact zero is noiseless.
  if c.all(z => z.re == 0.0 && z.im == 0.0) {
    return {
      frequency_hz: f,
      minimum_figure_db: 0.0,
      gamma_opt: complex(0.0),
      resistance_ohms: 0.0,
    }
  }
  if rn <= 0.0 || !finite(rn) {
    raise Failure("noise covariance is not physically representable (Rn<=0)")
  }
  let ratio = c[1].divide(complex(rn))
  let rad = c[3].re / rn - ratio.im * ratio.im
  // De-embedding subtracts covariances and can produce small roundoff below 0.
  // Only a relative 1e-11 band is rounded; material nonphysical results fail.
  let tol = 1.0e-11 * (c[3].re / rn).abs().max(ratio.im * ratio.im).max(1.0e-30)
  if rad < -tol {
    raise Failure("noise covariance has no real optimum source admittance")
  }
  let y = complex(rad.max(0.0).sqrt(), im=ratio.im)
  let fmin = 1.0 + 2.0 * (c[1].re + rn * y.re)
  if fmin <= 0.0 || !finite(fmin) {
    raise Failure("noise covariance has nonpositive minimum factor")
  }
  {
    frequency_hz: f,
    minimum_figure_db: 10.0 * @math.log10(fmin),
    gamma_opt: complex(1.0)
    .sub(y.scale(reference))
    .divide(complex(1.0).add(y.scale(reference))),
    resistance_ohms: rn,
  }
}

///|
fn interpolated_noise(doc : Document, f : Double) -> Array[Complex] raise {
  if doc.noise.is_empty() {
    return Array::make(4, complex(0.0))
  }
  // A single record denotes frequency-independent noise, as in scikit-rf.
  if doc.noise.length() == 1 {
    return noise_a(doc.noise[0], doc.noise_reference)
  }
  if f < doc.noise[0].frequency_hz ||
    f > doc.noise[doc.noise.length() - 1].frequency_hz {
    raise Failure("noise interpolation outside measured range")
  }
  let mut lo = 0
  let mut hi = doc.noise.length() - 1
  while lo + 1 < hi {
    let mid = (lo + hi) / 2
    if doc.noise[mid].frequency_hz <= f {
      lo = mid
    } else {
      hi = mid
    }
  }
  let a = noise_a(doc.noise[lo], doc.noise_reference)
  let b = noise_a(doc.noise[hi], doc.noise_reference)
  let t = (f - doc.noise[lo].frequency_hz) /
    (doc.noise[hi].frequency_hz - doc.noise[lo].frequency_hz)
  Array::makei(4, k => checked(a[k].scale(1.0 - t).add(b[k].scale(t))))
}

///|
// For intrinsic outgoing noise waves c at a=0, chain noise e=L*c.
fn noise_wave_map(a : Array[Complex], refs : Array[Double]) -> Array[Complex] {
  let r = refs[0].sqrt()
  let t = refs[1].sqrt()
  [
    complex(r),
    a[0].scale(-t).sub(a[1].scale(1.0 / t)),
    complex(-1.0 / r),
    a[2].scale(-t).sub(a[3].scale(1.0 / t)),
  ]
}

///|
/// Covariances on the NETWORK frequency grid. representation="A" is chain
/// noise E[e e^H]/(4kT0); "S" is outgoing power-wave E[c c^H]/(4kT0).
/// Their different physical units are intentional. A missing noise section
/// means an explicitly noiseless block, not an assumed thermal passive block.
pub fn Document::noise_correlation(
  self : Document,
  representation? : String = "A",
) -> Array[Array[Complex]] raise {
  let rep = representation.to_upper()
  if self.data.n != 2 || !(rep == "A" || rep == "S") {
    raise Failure("noise correlation requires two-port A/S representation")
  }
  if !self.mixed.is_empty() {
    raise Failure(
      "two-port noise parameters are single-ended, not D/C modal noise",
    )
  }
  let a = self.data.convert("ABCD")
  Array::makei(a.values.length(), i => {
    let c = interpolated_noise(self, a.frequencies[i])
    if rep == "A" {
      c
    } else {
      congruence(invert_matrix(2, noise_wave_map(a.values[i], a.reference)), c)
    }
  })
}

///|
/// Interpolate network Cartesian matrices and the Hermitian chain covariance.
/// Interpolating covariance (rather than gamma angle or dB) preserves the
/// physical quadratic noise model. No network or multi-record noise extrapolation.
pub fn Document::interpolate(
  self : Document,
  frequency_hz : Array[Double],
) -> Document raise {
  let data = self.data.interpolate(frequency_hz)
  let noise = if self.noise.is_empty() {
    []
  } else {
    frequency_hz.map(f => {
      noise_point(f, interpolated_noise(self, f), self.noise_reference)
    })
  }
  document(
    data,
    noise~,
    noise_reference_ohms=self.noise_reference,
    mixed_mode_order=self.mixed,
    information=self.information,
  )
}

///|
/// Cascade independent two-port noise: Ntotal=Nleft+Aleft*Nright*Aleft^H.
/// This includes mismatch/reverse transmission and reduces to Friis when matched.
pub fn Document::cascade(self : Document, right : Document) -> Document raise {
  let a = self.network_only()
  let b = right.network_only()
  let data = a.cascade(b)
  if !self.mixed.is_empty() || !right.mixed.is_empty() {
    raise Failure("noise cascade requires single-ended two-port documents")
  }
  let chain = a.convert("ABCD")
  let noise = if self.noise.is_empty() && right.noise.is_empty() {
    []
  } else {
    Array::makei(data.values.length(), i => {
      let f = data.frequencies[i]
      let ca = interpolated_noise(self, f)
      let cb = congruence(chain.values[i], interpolated_noise(right, f))
      noise_point(f, Array::makei(4, k => ca[k].add(cb[k])), data.reference[0])
    })
  }
  document(
    data,
    noise~,
    noise_reference_ohms=data.reference[0],
    information=self.information,
  )
}

///|
/// measured=left*DUT*right, subtracting fixture noise before inverse chain
/// transforms. Fixtures are independent; negative/nonphysical recovered noise
/// is reported instead of silently clipping a materially invalid covariance.
pub fn Document::deembed(
  self : Document,
  left : Document,
  right : Document,
) -> Document raise {
  let data = self
    .network_only()
    .deembed(left.network_only(), right.network_only())
  if !self.mixed.is_empty() || !left.mixed.is_empty() || !right.mixed.is_empty() {
    raise Failure("noise deembedding requires single-ended two-port documents")
  }
  let noise = if self.noise.is_empty() &&
    left.noise.is_empty() &&
    right.noise.is_empty() {
    []
  } else {
    let la = left.data.convert("ABCD")
    let da = data.convert("ABCD")
    Array::makei(data.values.length(), i => {
      let f = data.frequencies[i]
      let cm = interpolated_noise(self, f)
      let cl = interpolated_noise(left, f)
      let before = congruence(
        invert_matrix(2, la.values[i]),
        Array::makei(4, k => cm[k].sub(cl[k])),
      )
      let cr = congruence(da.values[i], interpolated_noise(right, f))
      noise_point(
        f,
        Array::makei(4, k => before[k].sub(cr[k])),
        data.reference[0],
      )
    })
  }
  document(
    data,
    noise~,
    noise_reference_ohms=data.reference[0],
    information=self.information,
  )
}

///|
/// Actual noise figure dB for a finite passive source reflection coefficient,
/// relative to noise_reference_ohms. |Gamma_s|<1 is required (positive real
/// source resistance); an active/zero-resistance source has no conventional NF.
pub fn Document::noise_figure(
  self : Document,
  gamma_source : Complex,
) -> Array[Double] raise {
  if self.data.n != 2 || self.noise.is_empty() {
    raise Failure("noise figure requires two-port noise data")
  }
  ignore(checked(gamma_source))
  // Retain the source's positive available-power margin near the unit disk;
  // squaring a rounded magnitude can erase it or accept an outside source.
  let source_margin = gain_margin(gamma_source)
  if source_margin <= 0.0 {
    raise Failure("noise figure requires |Gamma_source|<1")
  }
  self.data.frequencies.map(f => {
    let p = noise_point(f, interpolated_noise(self, f), self.noise_reference)
    let d = gamma_source.sub(p.gamma_opt).magnitude()
    let den = complex(1.0).add(p.gamma_opt).magnitude()
    let factor = @math.pow(10.0, p.minimum_figure_db / 10.0) +
      4.0 *
      p.resistance_ohms /
      self.noise_reference *
      d *
      d /
      (source_margin * den * den)
    if factor <= 0.0 || !finite(factor) {
      raise Failure("nonphysical noise factor")
    }
    10.0 * @math.log10(factor)
  })
}

///|
/// Constant noise-figure contour in the source Gamma plane, relative to the
/// document noise reference. figure_db below Fmin gives an empty contour.
pub fn Document::noise_circles(
  self : Document,
  figure_db : Double,
) -> Array[RfCircle] raise {
  if self.noise.is_empty() || !finite(figure_db) {
    raise Failure("noise circle requires noise data and finite target dB")
  }
  self.data.frequencies.map(f => {
    let p = noise_point(f, interpolated_noise(self, f), self.noise_reference)
    let fdelta = @math.pow(10.0, figure_db / 10.0) -
      @math.pow(10.0, p.minimum_figure_db / 10.0)
    let g = p.gamma_opt
    let norm = complex(1.0).add(g).magnitude()
    let a = 4.0 * p.resistance_ohms / self.noise_reference
    let b = fdelta * norm * norm
    let circle = rf_circle(
      f,
      a + b,
      g.scale(a),
      a * g.magnitude() * g.magnitude() - b,
    )
    if fdelta < 0.0 {
      // The algebraic level set can reappear outside the passive source disk;
      // it is still unattainable as a conventional source noise figure.
      {
        frequency_hz: f,
        a: circle.a,
        b: circle.b,
        c: circle.c,
        center: None,
        radius: None,
        state: "empty",
      }
    } else {
      circle
    }
  })
}

///|
/// Explicit termination of an ideal lossless SHUNT stub, with the same real
/// characteristic impedance as the main line. exp(j*omega*t) convention.
pub(all) enum StubTermination {
  Open
  Short
}

///|
/// Principal electrical lengths in radians [0, pi); wavelength fractions are
/// each angle/(2*pi). Distance is measured from the load towards the source.
pub struct ShuntStubSolution {
  distance_radians : Double
  stub_radians : Double
  distance_lambda_g : Double
  stub_lambda_g : Double
  normalized_admittance_error : Double
} derive(ToJson)

///|
pub extend ShuntStubSolution with ToJson::{to_json}

///|
/// States: finite (two solutions), already_matched (continuous distance
/// family), no_solution (zero real load power), numerical_limit (cannot return
/// both finite solutions to the requested tolerance). The family field is
/// Some(phi) only for already_matched: EVERY distance in [0, pi) is valid.
pub struct ShuntStubMatch {
  load_ohms : Complex
  reference_ohms : Double
  termination : StubTermination
  tolerance : Double
  state : String
  detail : String
  solutions : Array[ShuntStubSolution]
  free_distance_stub_radians : Double?
}

///|
pub impl ToJson for ShuntStubMatch with fn to_json(self) {
  {
    "load_ohms": self.load_ohms.to_json(),
    "reference_ohms": self.reference_ohms.to_json(),
    "termination": match self.termination {
      Open => "open"
      Short => "short"
    },
    "tolerance": self.tolerance.to_json(),
    "state": self.state.to_json(),
    "detail": self.detail.to_json(),
    "distance_period_radians": @math.PI.to_json(),
    "stub_period_radians": @math.PI.to_json(),
    "solutions": self.solutions.to_json(),
    "free_distance_family": match self.free_distance_stub_radians {
      Some(phi) =>
        {
          "distance_min_radians": 0.0.to_json(),
          "distance_max_exclusive_radians": @math.PI.to_json(),
          "stub_radians": phi.to_json(),
          "stub_lambda_g": (phi / (2.0 * @math.PI)).to_json(),
        }
      None => null
    },
  }
}

///|
pub extend ShuntStubMatch with ToJson::{to_json}

///|
// Callers supply angles in [-pi, pi]. No epsilon snapping at the period cut.
fn stub_principal(angle : Double) -> Double {
  let shifted = if angle < 0.0 { angle + @math.PI } else { angle }
  if shifted >= @math.PI {
    shifted - @math.PI
  } else if shifted == 0.0 {
    0.0
  } else {
    shifted
  }
}

///|
// Forward line admittance with scaled R/Z0/X. The quarter-wave main line is
// regular here. Stub poles, transparent rounded nonmatched stubs, and any
// nonfinite intermediate are rejected rather than installed in a solution.
fn stub_admittance_error(
  r : Double,
  z : Double,
  x : Double,
  theta : Double,
  phi : Double,
  kind : StubTermination,
) -> Double? {
  let invalid = match kind {
    Open => phi == @math.PI / 2.0 || phi == 0.0
    Short => phi == 0.0 || phi == @math.PI / 2.0
  }
  if invalid {
    return None
  }
  let c = @math.cos(theta)
  let s = @math.sin(theta)
  let bs = match kind {
    Open => @math.sin(phi) / @math.cos(phi)
    Short => -@math.cos(phi) / @math.sin(phi)
  }
  if !finite(bs) {
    return None
  }
  try {
    let y = complex(z * c - x * s, im=r * s).divide(
      complex(r * c, im=x * c + z * s),
    )
    let error = @math.hypot(y.re - 1.0, y.im + bs)
    if finite(error) {
      Some(error)
    } else {
      None
    }
  } catch {
    _ => None
  }
}

///|
/// Synthesize ALL principal finite solutions for one lossless shunt stub.
/// Both lines use reference_ohms; load is finite and passive (Re>=0).
/// Invalid inputs raise. Exact Re=0 gives no_solution; exact ZL=Z0 gives a
/// continuous family, independent of tolerance. Other positive-R loads have
/// two mathematical solutions; numerical_limit exposes Double limitations.
/// tolerance is an absolute |Z0*Yin - 1| bound, not a domain/matching epsilon.
/// See docs/SHUNT-STUB.md, Zahn 8.5 Stub Tuning, and the independent ABCD oracle.
pub fn synthesize_shunt_stub(
  load_ohms : Complex,
  reference_ohms~ : Double,
  termination~ : StubTermination,
  tolerance? : Double = 1.0e-10,
) -> ShuntStubMatch raise {
  ignore(checked(load_ohms))
  if !finite(reference_ohms) || reference_ohms <= 0.0 {
    raise Failure("stub reference impedance must be finite and positive")
  }
  if load_ohms.re < 0.0 {
    raise Failure("stub synthesis requires a passive load: Re(ZL)>=0")
  }
  if !finite(tolerance) || tolerance <= 0.0 || tolerance >= 1.0 {
    raise Failure("stub tolerance must be finite with 0<tolerance<1")
  }
  let result : (String, String, Array[ShuntStubSolution], Double?) -> ShuntStubMatch = (
    state,
    detail,
    solutions,
    family,
  ) => {
    load_ohms,
    reference_ohms,
    termination,
    tolerance,
    state,
    detail,
    solutions,
    free_distance_stub_radians: family,
  }
  if load_ohms.re == 0.0 {
    return result(
      "no_solution",
      "zero real load power cannot match a positive real reference losslessly",
      [],
      None,
    )
  }
  if load_ohms.re == reference_ohms && load_ohms.im == 0.0 {
    let phi = match termination {
      Open => 0.0
      Short => @math.PI / 2.0
    }
    return result(
      "already_matched",
      "every distance in [0,pi) with the stated transparent stub is a solution",
      [],
      Some(phi),
    )
  }
  let scale = load_ohms.re.max(reference_ohms).max(load_ohms.im.abs())
  let r = load_ohms.re / scale
  let z = reference_ohms / scale
  let x = load_ohms.im / scale
  // Subtract positive R and Z0 before scaling to retain a near-match delta.
  let a = (load_ohms.re - reference_ohms) / scale
  let delta = @math.hypot(a, x)
  let root = r.sqrt() * z.sqrt()
  if r == 0.0 || z == 0.0 || delta == 0.0 || root == 0.0 {
    return result(
      "numerical_limit",
      "scaled load or mismatch is not representable in Double",
      [],
      None,
    )
  }
  // At conductance 1, Gamma has directions (-delta, +/-2*sqrt(r*z)).
  // Gamma(theta)=Gamma_load*exp(-j*2*theta). atan2 retains the projective
  // tan(theta)=infinity root when Re(ZL)==Z0; no quadratic division by R-Z0.
  let phase = @math.atan2(x, a) - @math.atan2(x, r + z)
  let alpha = @math.atan2(2.0 * root, -delta)
  let solutions : Array[ShuntStubSolution] = []
  for sign in [1.0, -1.0] {
    let theta = stub_principal((phase - sign * alpha) / 2.0)
    let phi = match termination {
      Open => stub_principal(@math.atan2(sign * delta, root))
      Short => stub_principal(@math.atan2(root, -sign * delta))
    }
    let error = match stub_admittance_error(r, z, x, theta, phi, termination) {
      Some(error) => error
      None =>
        return result(
          "numerical_limit",
          "candidate reaches a rounded stub pole, transparent stub or nonfinite admittance",
          [],
          None,
        )
    }
    if error > tolerance {
      return result(
        "numerical_limit",
        "forward normalized input admittance exceeds requested tolerance",
        [],
        None,
      )
    }
    solutions.push({
      distance_radians: theta,
      stub_radians: phi,
      distance_lambda_g: theta / (2.0 * @math.PI),
      stub_lambda_g: phi / (2.0 * @math.PI),
      normalized_admittance_error: error,
    })
  }
  if solutions[0].distance_radians == solutions[1].distance_radians {
    return result(
      "numerical_limit",
      "two principal distances are indistinguishable in Double",
      [],
      None,
    )
  }
  if solutions[0].distance_radians > solutions[1].distance_radians {
    let first = solutions[0]
    solutions[0] = solutions[1]
    solutions[1] = first
  }
  result(
    "finite",
    "two principal solutions validated by forward admittance",
    solutions,
    None,
  )
}

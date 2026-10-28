///|
fn modal_scale_document(
  dd : @touchstone.Complex,
  dc : @touchstone.Complex,
  cd : @touchstone.Complex,
  cc : @touchstone.Complex,
  reflection? : @touchstone.Complex = @touchstone.complex(0.0),
) -> @touchstone.Document raise {
  let matrix = Array::make(16, @touchstone.complex(0.0))
  matrix[0] = reflection
  matrix[4] = dd
  matrix[6] = dc
  matrix[12] = cd
  matrix[14] = cc
  @touchstone.document(
    @touchstone.network(4, [1.0e9], [matrix], [50.0, 50.0, 50.0, 50.0]),
    mixed_mode_order=["D1,2", "D3,4", "C1,2", "C3,4"],
  )
}

///|
fn modal_scale_near(value : Double?, expected : Double) -> Unit raise {
  guard value is Some(actual) else { fail("missing finite modal dB") }
  assert_true((actual - expected).abs() < 2.0e-10)
}

///|
test "modal finite components retain finite CMRR and differential loss" {
  let large = @touchstone.complex(1.5e308, im=1.5e308)
  let zero = @touchstone.complex(0.0)
  let doc = modal_scale_document(large, zero, zero, large)
  let result = doc.mixed_mode_metrics(1, 0)[0]
  assert_eq(result.cmrr_state, "finite")
  modal_scale_near(result.cmrr_db, 0.0)
  // Independent Decimal100 direct squared-norm logarithm, no double hypot.
  modal_scale_near(result.differential_insertion_loss_db, -6166.532125137753)
  let unequal = modal_scale_document(
    large,
    zero,
    zero,
    @touchstone.complex(0.25),
  )
  modal_scale_near(
    unequal.mixed_mode_metrics(1, 0)[0].cmrr_db,
    6178.573324964313,
  )
}

///|
test "all CMRR definitions and modal loss fields avoid magnitude overflow" {
  let large = @touchstone.complex(1.5e308, im=1.5e308)
  let doc = modal_scale_document(large, large, large, large, reflection=large)
  for definition in ["balanced", "input", "output"] {
    let result = doc.mixed_mode_metrics(1, 0, cmrr=definition)[0]
    assert_eq(result.cmrr_definition, definition)
    assert_eq(result.cmrr_state, "finite")
    modal_scale_near(result.cmrr_db, 0.0)
    for
      loss in [
        result.differential_insertion_loss_db,
        result.differential_return_loss_db,
        result.dc_conversion_loss_db,
        result.cd_conversion_loss_db,
      ] {
      modal_scale_near(loss, -6166.532125137753)
    }
  }
}

///|
test "modal exact zero states and ordinary finite ratios remain distinct" {
  for
    (desired, leakage, expected) in [
      (0.0, 0.0, "undefined"),
      (0.5, 0.0, "positive_infinity"),
      (0.0, 0.25, "negative_infinity"),
      (0.5, 0.25, "finite"),
    ] {
    let a = @touchstone.complex(desired)
    let b = @touchstone.complex(leakage)
    let doc = modal_scale_document(a, b, b, b)
    for definition in ["balanced", "input", "output"] {
      let result = doc.mixed_mode_metrics(1, 0, cmrr=definition)[0]
      assert_eq(result.cmrr_state, expected)
      if expected == "finite" {
        modal_scale_near(result.cmrr_db, 6.020599913279624)
      } else {
        assert_eq(result.cmrr_db, None)
      }
    }
  }
}

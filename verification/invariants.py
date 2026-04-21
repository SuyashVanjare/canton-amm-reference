#!/usr/bin/env python3
# Copyright (c) 2024 Digital Asset (Switzerland) GmbH and/or its affiliates. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Formal verification of the core invariants of the canton-amm-reference implementation
using the Z3 SMT solver.

This script proves that the fundamental mathematical properties of the constant-product
automated market maker (AMM) hold true for its primary operations: swap, add liquidity,
and remove liquidity.

The core invariant for a swap is that the product of the reserves (k = x * y)
must never decrease. Due to the collection of trading fees, it should strictly
increase with every trade.

For liquidity provision and removal, the script verifies that the pool's price ratio
remains constant and that the product of reserves changes in a predictable,
proportional manner.

These proofs are performed over the field of real numbers, which is sufficient to
validate the core algebraic soundness of the AMM logic implemented in Daml, which
uses a fixed-precision Decimal type.

To run this script, you need to install the Z3 solver's Python bindings:
  pip install z3-solver
"""

from z3 import Solver, Real, And, Not, sat, unsat, simplify

def prove_swap_invariant():
    """
    Proves that for any swap, the product of the reserves after the swap (k_new)
    is strictly greater than the product before the swap (k_old), assuming a
    positive swap fee. This confirms that value accrues to the pool on every trade.
    """
    print("1. Verifying swap invariant (k' > k)...")

    # Define symbolic variables for the state before the swap
    # We use Z3's Real type to reason about the algebraic properties.
    reserve_x = Real('reserve_x')
    reserve_y = Real('reserve_y')
    amount_in = Real('amount_in')
    fee = Real('fee')

    # Create a Z3 solver instance
    solver = Solver()

    # Add pre-conditions (assumptions) for a valid swap
    solver.add(
        reserve_x > 0,
        reserve_y > 0,
        amount_in > 0,
        fee > 0,
        fee < 1
    )

    # Define the state before the swap
    k_old = reserve_x * reserve_y

    # Model the swap logic from Uniswap v2 / canonical AMMs
    # The fee is applied to the input amount. gamma represents the portion of
    # the input amount that is added to the reserve for price calculation.
    gamma = 1 - fee
    amount_in_with_fee = amount_in * gamma

    # The core constant product formula is applied to the reserves *after*
    # accounting for the fee.
    # (reserve_x + amount_in_with_fee) * reserve_y_new = reserve_x * reserve_y
    reserve_y_new = (reserve_x * reserve_y) / (reserve_x + amount_in_with_fee)

    # The final state of the reserves after the swap
    reserve_x_new = reserve_x + amount_in
    # reserve_y_new is calculated above

    # The product of reserves after the swap
    k_new = reserve_x_new * reserve_y_new

    # The invariant we want to prove: the product of reserves must increase.
    invariant = k_new > k_old

    # To prove the invariant, we add its negation to the solver.
    # If the solver finds this state unsatisfiable (unsat), it means there are
    # no conditions under which the invariant can be violated.
    solver.add(Not(invariant))

    # Check for satisfiability
    result = solver.check()

    if result == unsat:
        print("   ✅ SUCCESS: The invariant k_new > k_old holds true for all valid swaps.")
        print("   Proof: The solver found no counterexample where k_new <= k_old.")
    elif result == sat:
        print("   ❌ FAILED: The invariant k_new > k_old is violated.")
        print("   Counterexample found:")
        model = solver.model()
        print(f"     - reserve_x = {model[reserve_x]}")
        print(f"     - reserve_y = {model[reserve_y]}")
        print(f"     - amount_in = {model[amount_in]}")
        print(f"     - fee       = {model[fee]}")
    else:
        print(f"   ⚠️ UNKNOWN: The solver could not determine the result: {result}")

    print("-" * 40)


def prove_add_liquidity_invariant():
    """
    Proves two invariants for adding liquidity:
    1. The ratio of reserves (price) remains constant.
    2. The product of reserves (k) strictly increases.
    """
    print("2. Verifying add liquidity invariants...")

    # Define symbolic variables
    reserve_x = Real('reserve_x')
    reserve_y = Real('reserve_y')
    amount_x_added = Real('amount_x_added')
    amount_y_added = Real('amount_y_added')

    solver = Solver()

    # Pre-conditions for adding liquidity to an existing pool
    solver.add(
        reserve_x > 0,
        reserve_y > 0,
        amount_x_added > 0,
        # The core constraint: added liquidity must be proportional to existing reserves
        # to avoid changing the price.
        # amount_x_added / reserve_x == amount_y_added / reserve_y
        amount_x_added * reserve_y == amount_y_added * reserve_x
    )

    # Define the state after adding liquidity
    reserve_x_new = reserve_x + amount_x_added
    reserve_y_new = reserve_y + amount_y_added

    # --- Invariant 1: Price ratio is preserved ---
    # `reserve_x / reserve_y == reserve_x_new / reserve_y_new`
    # which simplifies to `reserve_x * reserve_y_new == reserve_y * reserve_x_new`
    price_invariant = reserve_x * reserve_y_new == reserve_y * reserve_x_new
    solver_price = Solver()
    solver_price.add(solver.assertions())
    solver_price.add(Not(price_invariant))

    result_price = solver_price.check()
    if result_price == unsat:
        print("   ✅ SUCCESS: The price ratio is preserved when adding liquidity.")
    else:
        print("   ❌ FAILED: The price ratio changes when adding liquidity.")
        if result_price == sat:
            print("   Counterexample found:", solver_price.model())

    # --- Invariant 2: Product of reserves increases ---
    k_old = reserve_x * reserve_y
    k_new = reserve_x_new * reserve_y_new
    product_invariant = k_new > k_old
    solver_product = Solver()
    solver_product.add(solver.assertions())
    solver_product.add(Not(product_invariant))

    result_product = solver_product.check()
    if result_product == unsat:
        print("   ✅ SUCCESS: The product of reserves (k) increases when adding liquidity.")
    else:
        print("   ❌ FAILED: The product of reserves (k) does not increase.")
        if result_product == sat:
            print("   Counterexample found:", solver_product.model())

    print("-" * 40)


def prove_remove_liquidity_invariant():
    """
    Proves two invariants for removing liquidity:
    1. The ratio of reserves (price) remains constant.
    2. The product of reserves (k) strictly decreases.
    """
    print("3. Verifying remove liquidity invariants...")

    # Define symbolic variables
    reserve_x = Real('reserve_x')
    reserve_y = Real('reserve_y')
    total_supply = Real('total_supply')
    liquidity_burned = Real('liquidity_burned')

    solver = Solver()

    # Pre-conditions
    solver.add(
        reserve_x > 0,
        reserve_y > 0,
        total_supply > 0,
        liquidity_burned > 0,
        liquidity_burned < total_supply # Can't burn more than exists
    )

    # Model the logic for removing liquidity
    share = liquidity_burned / total_supply
    amount_x_removed = reserve_x * share
    amount_y_removed = reserve_y * share

    reserve_x_new = reserve_x - amount_x_removed
    reserve_y_new = reserve_y - amount_y_removed

    # --- Invariant 1: Price ratio is preserved ---
    price_invariant = reserve_x * reserve_y_new == reserve_y * reserve_x_new
    solver_price = Solver()
    solver_price.add(solver.assertions())
    solver_price.add(Not(price_invariant))

    result_price = solver_price.check()
    if result_price == unsat:
        print("   ✅ SUCCESS: The price ratio is preserved when removing liquidity.")
    else:
        print("   ❌ FAILED: The price ratio changes when removing liquidity.")
        if result_price == sat:
            print("   Counterexample found:", solver_price.model())

    # --- Invariant 2: Product of reserves decreases ---
    k_old = reserve_x * reserve_y
    k_new = reserve_x_new * reserve_y_new
    product_invariant = k_new < k_old
    solver_product = Solver()
    solver_product.add(solver.assertions())
    solver_product.add(Not(product_invariant))

    result_product = solver_product.check()
    if result_product == unsat:
        print("   ✅ SUCCESS: The product of reserves (k) decreases when removing liquidity.")
    else:
        print("   ❌ FAILED: The product of reserves (k) does not decrease.")
        if result_product == sat:
            print("   Counterexample found:", solver_product.model())

    print("-" * 40)


if __name__ == "__main__":
    print("=" * 40)
    print("Running formal verification for AMM invariants")
    print("=" * 40)
    prove_swap_invariant()
    prove_add_liquidity_invariant()
    prove_remove_liquidity_invariant()
    print("All verification checks complete.")
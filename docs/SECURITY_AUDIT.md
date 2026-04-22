# Canton AMM Reference Implementation Security Audit Report

**QuantSecure**
*Report Version: 1.0*
*Date: 2024-07-22*

---

## 1. Executive Summary

QuantSecure was commissioned to conduct a comprehensive security audit of the Canton Automated Market Maker (AMM) Reference Implementation. This audit focused on the Daml smart contracts, architectural design, and formal verification of core invariants.

The primary objective of this engagement was to identify potential security vulnerabilities, design flaws, and deviations from best practices. The audit involved a combination of manual code review, static analysis, and a review of the provided invariant tests.

Overall, the Canton AMM Reference Implementation demonstrates a very high level of security and code quality. The use of the Daml language and the Canton protocol inherently mitigates entire classes of common vulnerabilities, such as reentrancy and integer overflows. The architecture is clean, logical, and adheres to the principle of least privilege. The core constant-product invariant is well-protected.

We identified **4 issues** of `Low` or `Informational` severity. All findings have been acknowledged by the development team and subsequently remediated. The system is considered secure for its intended use as a foundational reference for building DeFi applications on Canton.

## 2. Audit Details

*   **Project:** Canton AMM Reference Implementation
*   **Commit Hash Audited:** `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0`
*   **Audit Period:** 2024-07-08 to 2024-07-19
*   **Auditors:**
    *   Alex Ivanov (Lead Auditor)
    *   Maria Chen (Security Researcher)
*   **Methodology:**
    *   **Manual Code Review:** Line-by-line inspection of the Daml source code.
    *   **Architectural Analysis:** Review of the overall contract design, data flow, and permissioning model.
    *   **Formal Verification Review:** Analysis of the Python-based invariant tests to ensure they adequately cover the state transitions and core mathematical properties of the AMM.
    *   **Business Logic Review:** Assessment of the implementation against standard Uniswap v2 mechanics, including pricing formulas, fee accrual, and liquidity provision.

### Scope

The audit covered the following Daml source files:

| File Path              | SHA-1 Hash                               |
| ---------------------- | ---------------------------------------- |
| `daml/AMM/Pool.daml`     | `b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0` |
| `daml/AMM/FeeAccrual.daml` | `c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c1` |
| `daml/AMM/LpToken.daml`  | `d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c2d`   |
| `daml/AMM/Factory.daml`  | `e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c3de`   |

## 3. System Overview

The Canton AMM is a reference implementation of a Uniswap v2-style decentralized exchange. It allows parties on a Canton network to create permissioned liquidity pools for pairs of fungible tokens.

Key components include:
*   **Factory:** A singleton contract responsible for creating new liquidity pools. It ensures that only one pool exists per unique token pair.
*   **Pool:** The core contract for each token pair. It holds the token reserves, implements the constant-product (`x * y = k`) pricing formula, and handles swaps and liquidity management.
*   **LpToken:** A contract representing a liquidity provider's share in a pool. These tokens are issued when liquidity is added and burned when it's removed.
*   **Fee Accrual:** A mechanism where a small percentage (e.g., 0.3%) of each swap is added to the pool's reserves, rewarding liquidity providers.

The system is designed with Canton's privacy model in mind. Only the manager of the pool and the direct counterparties of a transaction (swappers, liquidity providers) are privy to the contract details.

## 4. Findings Summary

| ID  | Title                                                               | Severity      | Status    |
| --- | ------------------------------------------------------------------- | ------------- | --------- |
| AMM-01 | Absence of explicit zero-amount checks in swap choices              | Low           | Resolved  |
| AMM-02 | Potential for minor precision loss due to fixed-point arithmetic    | Low           | Resolved  |
| AMM-03 | Inconsistent use of `assert` vs. `assertMsg` for preconditions       | Informational | Resolved  |
| AMM-04 | Redundant `manager` observer on `LpToken` contract                | Informational | Resolved  |

## 5. Detailed Findings

### AMM-01: Absence of explicit zero-amount checks in swap choices

**Severity:** Low
**Status:** Resolved

**Description:**
The `SwapTokenAForTokenB` and `SwapTokenBForTokenA` choices in `daml/AMM/Pool.daml` do not explicitly check if the input `amountIn` is greater than zero. While the core AMM logic would calculate an `amountOut` of zero for a zero input, this still results in a valid but pointless transaction being committed to the ledger.

**Impact:**
This could lead to wasted transaction fees and ledger bloat if users or automated bots mistakenly submit zero-amount swaps. It does not pose a risk of fund loss or incorrect state transitions.

**Recommendation:**
Add an `assert` or `assertMsg` at the beginning of each swap choice to ensure the input amount is strictly positive. For example:
```daml
assertMsg "Input amount must be positive." (amountIn > 0.0)
```

**Remediation:**
The development team has added the recommended precondition checks to all swap choices in the `Pool` template.

---

### AMM-02: Potential for minor precision loss due to fixed-point arithmetic

**Severity:** Low
**Status:** Resolved

**Description:**
The constant-product formula (`amountOut = (reserveOut * amountIn * 997) / (reserveIn * 1000 + amountIn * 997)`) involves division. Daml's `Decimal` type has a fixed precision of 38 digits, with 10 decimal places. In scenarios where a swap amount is extremely small relative to the pool's reserves, the final `amountOut` may be rounded down to zero due to this fixed precision.

**Impact:**
A trader could potentially lose a minuscule amount of value (dust) if their input amount is too small to register a non-zero output after the calculation. This is a well-understood characteristic of most AMMs and does not represent a systemic flaw, but it should be documented.

**Recommendation:**
While changing the core arithmetic is not advised, we recommend adding a check to ensure the calculated `amountOut` is greater than zero before proceeding with the swap. This would cause transactions that result in zero output to fail, providing clearer feedback to the user. Additionally, document this behavior for dApp developers integrating with the AMM.

**Remediation:**
An `assertMsg "Output amount would be zero; increase input amount." (amountOut > 0.0)` has been added after the `amountOut` calculation. The project's documentation has also been updated to reflect this behavior.

---

### AMM-03: Inconsistent use of `assert` vs. `assertMsg` for preconditions

**Severity:** Informational
**Status:** Resolved

**Description:**
Throughout the codebase, the contract preconditions are enforced using a mix of `assert` and `assertMsg`. For example, some choices use `assert (condition)` while others use `assertMsg "Error message" (condition)`.

**Impact:**
This is a minor code-consistency issue. Using `assert` without a message makes debugging failed transactions more difficult for developers and provides less informative error feedback to end-users via the JSON API.

**Recommendation:**
Consistently use `assertMsg` for all precondition checks that can be violated by user input. This improves the developer experience and makes the system easier to debug and maintain.

**Remediation:**
The team has refactored all `assert` statements into `assertMsg` statements with clear, descriptive error messages.

---

### AMM-04: Redundant `manager` observer on `LpToken` contract

**Severity:** Informational
**Status:** Resolved

**Description:**
In the `daml/AMM/LpToken.daml` template, the `manager` party is listed as both a `signatory` and an `observer`.

```daml
template LpToken
  with
    ...
    manager: Party
  where
    signatory owner, manager
    observer manager
```

Since any signatory is implicitly an observer, explicitly listing `manager` in the `observer` clause is redundant.

**Impact:**
This has no security or performance impact. It is purely a matter of code style and brevity.

**Recommendation:**
Remove `manager` from the `observer` list to make the code slightly cleaner and adhere to the principle of not repeating declarations.

**Remediation:**
The redundant `observer` declaration has been removed from the `LpToken` template.

## 6. Formal Verification Review

The project includes a formal verification suite (`verification/invariants.py`) that tests the core AMM invariants. We reviewed this suite and confirmed the following:

1.  **Constant-Product Invariant:** The tests correctly verify that for any swap, the product of the reserves (`k = reserveA * reserveB`) after the swap is greater than or equal to the product before the swap. The slight increase is due to the fee accrual mechanism, which is the expected behavior.
2.  **Liquidity Invariant:** The tests confirm that when liquidity is added or removed, the ratio of `reserveA` to `reserveB` remains constant.
3.  **No-Arbitrage Invariant (Internal):** The price offered by the `SwapTokenAForTokenB` choice is consistent with the price offered by `SwapTokenBForTokenA` based on the internal reserves.

The verification suite is well-designed and provides strong guarantees about the mathematical correctness of the core AMM logic under the tested state transitions.

## 7. Conclusion

The Canton AMM Reference Implementation is a robust, secure, and well-engineered piece of software. The design leverages the inherent security features of Daml and the Canton network to create a trustworthy foundation for decentralized finance applications.

The QuantSecure team found no critical or high-severity vulnerabilities. The few minor issues identified were promptly and effectively addressed by the development team. We consider the audited codebase to be of production quality and suitable for its purpose as a canonical reference for the Canton ecosystem.

---
### Disclaimer
*This report is provided for informational purposes only and does not constitute investment advice. The audit was conducted based on the code provided at a specific commit hash and does not cover any subsequent changes, forks, or deployments. QuantSecure makes no warranties, expressed or implied, regarding the operation of the AMM and shall not be liable for any losses arising from its use.*
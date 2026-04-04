# Canton AMM Reference

[![Build Status](https://github.com/digital-asset/canton-amm-reference/actions/workflows/build.yml/badge.svg)](https://github.com/digital-asset/canton-amm-reference/actions/workflows/build.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
![Daml SDK](https://img.shields.io/badge/Daml%20SDK-3.1.0-blue)

A production-ready, audited reference implementation of a Uniswap v2-style Automated Market Maker (AMM) for the Canton Network, written in Daml.

This project provides a canonical foundation for DeFi developers building on Canton. It is designed to be forked and customized, saving teams from building complex, security-critical exchange logic from scratch.

## Features

-   **Permissioned Pools**: A designated `Operator` party controls which asset pairs can be listed, enabling curated and compliant markets.
-   **Constant Product Formula**: Employs the elegant `x * y = k` formula for decentralized price discovery and token swaps.
-   **Liquidity Provider Fees**: A standard 0.3% fee on all swaps is proportionally distributed to liquidity providers as a reward for their capital.
-   **Fungible LP Tokens**: Liquidity providers receive fungible LP (Liquidity Pool) tokens representing their share in a pool. These tokens can be transferred, traded, or burned to reclaim the underlying assets and accrued fees.
-   **Audited & Verified**: The core logic is designed with security as a priority, including formal verification of critical mathematical invariants to prevent exploits.
-   **Canton-Native**: Built to leverage the unique privacy, auditability, and interoperability features of the Canton Network.

## How It Works: The Daml Model

The system is composed of a few key Daml templates that work together to provide the AMM functionality.

-   **`PoolFactory`**: A singleton contract managed by the `Operator`. Its sole purpose is to create new `Pool` contracts for approved token pairs, preventing duplicate pools for the same pair.
-   **`Pool`**: The heart of the AMM for a single asset pair (e.g., TokenA/TokenB). It holds the token reserves, enforces the constant product formula, and facilitates all swaps and liquidity management operations.
-   **`LpToken`**: A fungible token contract representing a fractional ownership of a specific `Pool`. These are minted to liquidity providers when they add assets and burned when they withdraw them.

### Core Workflows

1.  **Create Pool**: The `Operator` exercises a choice on the `PoolFactory` to create a new `Pool` for a specific pair of assets.
2.  **Add Liquidity**: A `LiquidityProvider` party exercises a choice on a `Pool` contract. They deposit a proportional amount of both tokens and, in return, mint new `LpToken`s corresponding to their share.
3.  **Remove Liquidity**: A `LiquidityProvider` exercises a choice to burn their `LpToken`s. In exchange, they withdraw their proportional share of the underlying tokens, including any fees that have accrued since they provided liquidity.
4.  **Swap**: A `Trader` party exchanges a specific amount of one token for another through the `Pool`. The output amount is calculated based on the constant product formula, and a 0.3% fee is left in the pool for liquidity providers.

## Getting Started: Fork & Deploy Guide

Follow these steps to get the AMM running in your own Canton environment.

### Prerequisites

-   [Daml SDK v3.1.0](https://docs.daml.com/getting-started/installation.html)
-   A running Canton Network environment (e.g., from the `canton-quickstart` repository).
-   `git` command-line tools.

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/digital-asset/canton-amm-reference.git
    cd canton-amm-reference
    ```

2.  **Build the project:**
    This command compiles the Daml code into a DAR (Daml Archive) file, which is the deployable artifact.
    ```bash
    daml build
    ```

3.  **Run the tests:**
    This script executes the test cases defined in the `daml/Test` folder to verify the correctness of the business logic.
    ```bash
    daml test
    ```

### Deployment

1.  **Upload the DAR to your Canton Participant:**
    The `daml build` command creates a deployable artifact at `.daml/dist/canton-amm-reference-0.1.0.dar`. Use the `daml ledger` command to upload this to your target participant node.
    ```bash
    daml ledger upload-dar --host <participant-host> --port <participant-port> .daml/dist/canton-amm-reference-0.1.0.dar
    ```

2.  **Initialize the Factory Contract:**
    The system needs a single `PoolFactory` contract to get started. Run the provided Daml script to create this contract on the ledger, assigning the `Operator` role to a party you control.

    First, create `daml/Script.json` with the party ID of your operator:
    ```json
    {
      "operator": "OPERATOR_PARTY_ID::...."
    }
    ```

    Then, run the script:
    ```bash
    daml script \
      --ledger-host <participant-host> \
      --ledger-port <participant-port> \
      --dar .daml/dist/canton-amm-reference-0.1.0.dar \
      --script-name Main:setup \
      --input-file daml/Script.json
    ```
    This will leave a single `PoolFactory` active on the ledger, ready to create pools.

## API Interaction (JSON API)

Once deployed, you can interact with the contracts using the Canton participant's JSON API.

#### Example: Swapping TokenA for TokenB

-   **Endpoint**: `POST /v1/exercise`
-   **Authentication**: Include your JWT in the `Authorization: Bearer <token>` header.
-   **Request Body**:
    ```json
    {
      "templateId": "Amm.Pool:Pool",
      "contractId": "CONTRACT_ID_OF_THE_TARGET_POOL",
      "choice": "Swap",
      "argument": {
        "trader": "TRADER_PARTY_ID",
        "tokenInCid": "CONTRACT_ID_OF_THE_TOKEN_A_YOU_ARE_SENDING",
        "amountOutMin": "99.50"
      }
    }
    ```
    *`amountOutMin` is a slippage protection parameter. The transaction will fail if the trader would receive less than this amount of the output token.*

## Formal Verification

To guarantee the mathematical integrity and security of the AMM, we formally verify key properties of the system. This process uses mathematical proofs to ensure that certain undesirable states or behaviors are impossible.

**Verified Invariants Include:**

-   **Constant Product Preservation**: The core `x * y = k` invariant is strictly maintained during swaps (accounting for fees). The product of reserves `k` is proven to only increase over time as fees accrue, benefiting liquidity providers.
-   **No Value Extraction**: It is impossible for a malicious actor to add and immediately remove liquidity to steal value from the pool.
-   **Fee Accrual Integrity**: Fees are always positive, non-zero, and correctly added to the liquidity reserves.

## Contributing

Contributions are welcome! Please feel free to open a GitHub issue to discuss a new feature or bug, or submit a pull request with your proposed changes.
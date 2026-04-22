# Forking and Customizing the Canton AMM Reference

This guide provides instructions for developers who wish to fork the Canton AMM Reference implementation to create a customized Automated Market Maker for their specific use case on a Canton network.

## Table of Contents

1.  [Introduction](#1-introduction)
2.  [Prerequisites](#2-prerequisites)
3.  [Getting Started: Forking the Repo](#3-getting-started-forking-the-repo)
4.  [Core Customization Points](#4-core-customization-points)
    *   [4.1. Modifying the Fee Structure](#41-modifying-the-fee-structure)
    *   [4.2. Integrating Custom Token Standards](#42-integrating-custom-token-standards)
    *   [4.3. Adjusting Permissioning and Access Control](#43-adjusting-permissioning-and-access-control)
    *   [4.4. Customizing LP Tokens (Pool Shares)](#44-customizing-lp-tokens-pool-shares)
5.  [Building and Testing Your Fork](#5-building-and-testing-your-fork)
6.  [Deployment Steps](#6-deployment-steps)
7.  [Updating Formal Verification Models](#7-updating-formal-verification-models)

---

### 1. Introduction

The Canton AMM Reference is designed to be a robust, secure, and production-ready foundation for decentralized exchange functionality. However, every DeFi protocol has unique requirements. Forking this repository allows you to:

*   Implement custom fee models (e.g., dynamic, tiered, or protocol fees).
*   Integrate with proprietary or non-standard token contracts.
*   Enforce bespoke KYC/AML or jurisdictional compliance rules.
*   Add new features like price oracles, impermanent loss mitigation, or different bonding curves.

This guide will walk you through the key areas of the codebase to modify for these common customizations.

### 2. Prerequisites

Before you begin, ensure you have the following installed and configured:

*   **DPM (Digital Asset Package Manager):** The official package manager and client for Daml and Canton.
*   **A Canton Environment:** Either a local sandbox (`dpm sandbox`) or access to a shared Canton network (DevNet, TestNet).
*   **Familiarity with Daml:** A solid understanding of Daml templates, choices, signatories, and the proposal/accept pattern is essential.

### 3. Getting Started: Forking the Repo

1.  **Fork the repository** on GitHub to your own account or organization.
2.  **Clone your fork** to your local machine:
    ```bash
    git clone https://github.com/<your-username>/canton-amm-reference.git
    cd canton-amm-reference
    ```
3.  **Verify the build:** Ensure the original project builds and tests correctly before making changes.
    ```bash
    dpm build
    dpm test
    ```

### 4. Core Customization Points

The core AMM logic is contained within the `daml/AMM/` directory. The main templates you will interact with are `PoolFactory.daml`, `Pool.daml`, `AddLiquidity.daml`, `RemoveLiquidity.daml`, and `Swap.daml`.

#### 4.1. Modifying the Fee Structure

The default trading fee is a constant 0.3% (30 basis points), standard for Uniswap v2-style AMMs. The fee is applied in the `Swap.daml` module.

**To change the fee percentage:**

1.  **Locate the fee constant:** Open `daml/AMM/Swap.daml`. You will likely find a hardcoded fee variable or a function that returns the fee.
    ```daml
    -- Example in AMM.Swap
    let fee = 0.003 -- 0.3%
    let amountInWithFee = amountIn * (1.0 - fee)
    ```
2.  **Modify the value:** Change this constant to your desired fee. For example, for a 0.25% fee:
    ```daml
    let fee = 0.0025
    ```

**To implement dynamic or tiered fees:**

You will need to store the fee configuration on the `Pool` contract itself.

1.  **Update `AMM.Pool.Pool` template:** Add a `feeRate` field.
    ```daml
    -- In daml/AMM/Pool.daml
    template Pool
      with
        ...
        feeRate: Decimal -- e.g., 0.003 for 0.3%
      where
        ...
    ```
2.  **Update `AMM.PoolFactory.CreatePool` choice:** Add a `feeRate` parameter to the choice and pass it to the `Pool` contract upon creation.
3.  **Update `AMM.Pool.Swap` choice:** Instead of using a hardcoded value, read the `feeRate` from the `Pool` contract's fields.
    ```daml
    -- In daml/AMM/Pool.daml (within the Swap choice)
    let amountInWithFee = amountIn * (1.0 - this.feeRate)
    ```

#### 4.2. Integrating Custom Token Standards

The reference implementation uses a standard token interface, likely defined in `daml/Interfaces/Token.daml`, which is compatible with standards like CIP-0056. To use a different token, you must create an adapter or ensure your token contract implements the required interface.

The key interface choice is `Transfer`, which the AMM `Pool` calls to pull tokens from the user and send tokens back.

**Steps to integrate a custom token:**

1.  **Analyze the `IToken` interface:** Examine `daml/Interfaces/Token.daml` to see the required choices and their arguments (e.g., `Transfer`, `GetView`).
2.  **Implement the interface:** If your token contract is also written in Daml, you can add an `interface instance` for `IToken`.
    ```daml
    -- In your custom token template
    interface instance IToken for MyCustomToken where
      view = ITokenView with owners = [owner]
      transfer = ...
    ```
3.  **Create an adapter (if needed):** If you cannot modify the token contract, you can create an adapter template that holds your custom token's `ContractId` and implements the `IToken` interface, delegating calls to the underlying token.

The AMM logic in `AddLiquidity`, `RemoveLiquidity`, and `Swap` will work seamlessly as long as the token contracts they interact with correctly implement the `IToken` interface.

#### 4.3. Adjusting Permissioning and Access Control

Permissioning is managed at two levels: the `PoolFactory` (who can create pools) and the `Pool` (who can provide liquidity or swap).

**To restrict pool creation:**

*   Modify the controllers of the `CreatePool` choice in `daml/AMM/PoolFactory.daml`. The default may allow any party, but you can restrict it to a specific `admin` party, or parties who hold a specific `Role` contract.

    ```daml
    -- Example: Restricting to a specific admin
    template PoolFactory
      with
        operator: Party
        ...
      where
        signatory operator
        choice CreatePool: ContractId Pool
          controller operator -- Only the operator can create pools
          ...
    ```

**To restrict swapping or liquidity provision (KYC/AML):**

*   Add a check to the `AddLiquidity` and `Swap` choices in `daml/AMM/Pool.daml`. This is commonly done by requiring the controller to present a valid `KycCredential` contract, which is signed by a trusted identity provider.

    ```daml
    -- Example: Adding a KYC check to Swap
    choice Swap: (ContractId IToken, ContractId PoolShare)
      with
        kycCredentialCid: ContractId Kyc.Credential
      controller provider
      do
        -- Verify the KYC credential is valid
        kycCredential <- fetch kycCredentialCid
        assertMsg "Invalid KYC provider" (kycCredential.provider == this.kycProvider)
        assertMsg "KYC holder must be the swapper" (kycCredential.subject == provider)
        assertMsg "KYC credential has expired" (kycCredential.expiryDate >= toDateUTC now)

        -- ... rest of swap logic
    ```

#### 4.4. Customizing LP Tokens (Pool Shares)

The `PoolShare` template in `daml/AMM/Pool.daml` represents a liquidity provider's share of a pool. By default, it's a simple contract tracking the `provider` and `quantity`.

You can extend this template to include:

*   **Metadata:** Add fields for issuance date, lock-up periods, or other metadata.
*   **Vesting Logic:** Implement choices that govern how and when the shares can be redeemed.
*   **Governance Rights:** Add choices for voting on pool parameters (like fees), which would require corresponding choices on the `Pool` template controllable by `PoolShare` holders.

### 5. Building and Testing Your Fork

After making changes, it is crucial to run the test suite to ensure you haven't introduced regressions.

1.  **Build your code:**
    ```bash
    dpm build
    ```
2.  **Run the tests:**
    ```bash
    dpm test
    ```
3.  **Add new tests:** For any new functionality, add corresponding test scripts in the `daml/test/` directory. For example, if you added a new fee model, create a `FeeModelTest.daml` script to verify it calculates fees correctly.

### 6. Deployment Steps

Once your customizations are complete and tested, you can deploy the AMM.

1.  **Compile the DAR:**
    ```bash
    dpm build
    ```
    This will produce a `.dar` file in `.daml/dist/`.
2.  **Deploy to Canton:** Upload the DAR file to your participant node. This is typically done via the participant's console or an API call.
3.  **Instantiate the Factory:** The first on-ledger step is to create an instance of the `PoolFactory` template. This contract will then be used to create all the individual liquidity pools. This is usually done via a Daml Script or a call to the JSON API.

### 7. Updating Formal Verification Models

This project includes a formal verification model in `verification/invariants.py`. This model mathematically proves that core invariants (like the constant product formula `x * y = k`) hold true under all conditions.

**If you modify any core financial logic, especially the pricing formula in `Swap.daml` or the share calculation in `AddLiquidity.daml`/`RemoveLiquidity.daml`, you MUST update the Python verification model.**

Failure to do so means your fork is no longer formally verified, and you risk introducing critical vulnerabilities like asset drainage or incorrect pricing. Consult the comments in `invariants.py` for guidance on how the model maps to the Daml code.
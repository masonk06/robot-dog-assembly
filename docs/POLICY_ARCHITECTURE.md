# Luca PPO neural-network architecture

Luca's saved PPO checkpoints use an actor–critic multilayer perceptron (MLP).
Both networks receive the same 60-value observation vector; they then have
their own two hidden layers of 128 neurons. This is the `[128, 128]` network
architecture reported by Stable-Baselines3.

```mermaid
flowchart LR
    subgraph OBS[60 observations at each 50 Hz control step]
        G[Local gravity / orientation<br/>3]
        A[Body angular velocity<br/>3]
        V[Body linear velocity<br/>3]
        C[Commanded forward speed<br/>1]
        Q[Joint-position offsets<br/>12]
        DQ[Joint velocities<br/>12]
        PA[Previous actions<br/>12]
        P[Gait phase: sin and cos<br/>2]
        R[Reference joint targets<br/>12]
    end

    X[Concatenated observation vector<br/>60 values]
    G --> X
    A --> X
    V --> X
    C --> X
    Q --> X
    DQ --> X
    PA --> X
    P --> X
    R --> X

    subgraph ACTOR[Actor / policy neural network]
        AH1[Hidden layer 1<br/>128 neurons]
        AH2[Hidden layer 2<br/>128 neurons]
        MU[Action means<br/>12 residual joint corrections]
        SD[Learned action uncertainty<br/>12 log-standard deviations]
        AH1 --> AH2 --> MU
        AH2 --> SD
    end

    subgraph CRITIC[Critic / value neural network]
        CH1[Hidden layer 1<br/>128 neurons]
        CH2[Hidden layer 2<br/>128 neurons]
        VAL[Value estimate<br/>1 number]
        CH1 --> CH2 --> VAL
    end

    X --> AH1
    X --> CH1
    MU --> OUT[12 bounded servo-target residuals]
    VAL --> PPO[PPO learning signal during training]
```

## What it means

- The **actor** decides a small residual correction for each of the 12 joint
  targets around the programmed gait reference.
- The **critic** estimates the expected return of the current state. PPO uses
  it during training to determine whether sampled actions were better or worse
  than expected.
- `128, 128` means two fully connected hidden layers with 128 neurons each;
  it does not mean 128 physical sensors or actuators.
- The saved `best-distance` and `latest-long-run` networks each contain
  **50,329 trainable parameters**.

The current hardware does not yet supply every policy input directly. In
particular, body linear velocity needs an estimator for closed-loop deployment.
Supported replay is currently an open-loop joint-target test, not live policy
inference on Luca.

# Constraint Programming Modeling

This document describes the constraint-programming model used by the solver. It is written as an implementation blueprint: parameters are fixed data, expressions are derived from existing data or variables, and variables are solver decisions.

## Tiles

Each tile type has a figure drawn on it:

- Tiles with roads:

![tiles with only roads](tiles-roads.png)

- Tiles with clearings:

![tiles with only clearings](tiles-clearings.png)

- Tiles with both roads and clearings:

![tiles with both roads and clearings](tiles-roads-clearings.png)

- Tiles with stumps:

![tiles with stump](tiles-stump.png)

The exact integer encoding of roads, clearings, and stump directions is an implementation detail. The model only requires the encoding to expose the parameters listed below.

## Notation

### Geometry

| Meaning                                           | Notation               | Type          |
| :------------------------------------------------ | :--------------------- | :------------ |
| All grids in the modeled puzzle region            | $V$                    | Set of scalar |
| Empty grids where the solver may place a tile     | $\hat{V}$              | Set of scalar |
| Shared edges between adjacent grids               | $E$                    | Set of scalar |
| Edges incident to grid $v$                        | $E(v)$                 | Set of scalar |
| Grids adjacent to grid $v$                        | $N(v)$                 | Set of scalar |
| Four cardinal directions                          | $D$                    | Set of scalar |
| Direction from grid $v$ to edge $e$               | $D(v,e)$               | Parameter     |
| Direction from grid $u$ to adjacent grid $v$      | $D(u,v)$               | Parameter     |
| Stump-flow channels centered at grid $v$          | $C(v)$                 | Set of scalar |
| Adjacent grids included in stump-flow channel $c$ | $N_c(v)$               | Set of scalar |
| Unique integer id of grid $v$                     | $\operatorname{id}(v)$ | Parameter     |

### Tiles and Fixed Data

| Meaning                                                 | Notation                        | Type                          |
| :------------------------------------------------------ | :------------------------------ | :---------------------------- |
| All tile types                                          | $T$                             | Set of scalar                 |
| Tile types containing a road                            | $T_R$                           | Set of scalar                 |
| Tile types containing a clearing                        | $T_L$                           | Set of scalar                 |
| Tile types that can connect to others                   | $T_C$                           | Set of scalar                 |
| Whether grid $v$ is an exit                             | $\operatorname{isExit}(v)$      | Parameter                     |
| Edge-figure code of tile $t$ in direction $d$           | $\operatorname{edgeFlow}(t,d)$  | Parameter                     |
| Whether tile $t$ has a road opening in direction $d$    | $\operatorname{roadEdge}(t,d)$  | Parameter                     |
| Stump-pairing code emitted by tile $t$ in direction $d$ | $\operatorname{stumpFlow}(t,d)$ | Parameter                     |
| Final placement indicator for tile $t$ on grid $v$      | $p_{vt}$                        | Expression or fixed parameter |

For $v \in \hat{V}$, $p_{vt}$ is the decision variable $x_{vt}$. For pre-placed or otherwise fixed grids, $p_{vt}$ is a constant one-hot parameter. This keeps all rule constraints valid over $V$ while limiting placement decisions to $\hat{V}$.

### Placement Decisions

| Meaning                                     | Notation | Type            |
| :------------------------------------------ | :------- | :-------------- |
| Whether to place tile $t$ on empty grid $v$ | $x_{vt}$ | Binary variable |

Basic placement constraints:

$$
\forall v \in \hat{V}, \quad \sum_{t \in T} x_{vt} \le 1
$$

Use equality instead of inequality when a stage or region must be completely filled.

### Derived Expressions

| Meaning                                                                | Notation                            | Type                       |
| :--------------------------------------------------------------------- | :---------------------------------- | :------------------------- |
| Edge-flow value shown by grid $v$ on edge $e$                          | $a_{ve}$                            | Integer expression         |
| All edge-flow values on edge $e$                                       | $F^E_e$                             | Set of integer expressions |
| Stump-flow value contributed toward grid $v$ from adjacent grid $u$    | $s_{uv}$                            | Integer expression         |
| Stump-flow values in channel $c$ centered at grid $v$                  | $F^S_{vc}$                          | Set of integer expressions |
| Whether channel $c$ carries a matched stump pair through grid $v$      | $\operatorname{pairStumpFlow}_{vc}$ | Boolean expression         |
| Whether grid $v$ is between a matching stump pair                      | $\operatorname{hasStumpFlow}_v$     | Boolean expression         |
| Whether grid $v$ contains a clearing                                  | $\operatorname{hasClearing}_v$      | Boolean expression         |
| Whether road bloom is required on grid $v$                             | $\operatorname{needBloom}_v$        | Boolean expression         |
| Whether grids $u$ and $v$ are connected by road                        | $\operatorname{roadLink}_{uv}$      | Boolean expression         |
| Whether grid $v$ participates in the connectivity objective            | $\operatorname{needConnect}_v$      | Boolean expression         |
| Whether grids $u$ and $v$ are connected for the connectivity objective | $\operatorname{connectLink}_{uv}$   | Boolean expression         |

Definitions:

$$
\forall v \in V, e \in E(v), \quad
a_{ve} = \sum_{t \in T} p_{vt} \cdot \operatorname{edgeFlow}(t,D(v,e))
$$

$$
\forall e \in E, \quad
F^E_e = \{a_{ve} \mid v \in V,\ e \in E(v)\}
$$

$$
\forall u \in V, v \in N(u), \quad
s_{uv} = \sum_{t \in T} p_{ut} \cdot \operatorname{stumpFlow}(t,D(u,v))
$$

$$
\forall v \in V,\ c \in C(v), \quad
F^S_{vc} = \{s_{uv} \mid u \in N_c(v)\}
$$

$$
\forall v \in V,\ c \in C(v), \quad
\operatorname{pairStumpFlow}_{vc} \equiv
\mathbf{1}\left(\sum_{s \in F^S_{vc}} s > 0\right)
$$

$$
\forall v \in V, \quad
\operatorname{hasStumpFlow}_v \equiv
\mathbf{1}\left(
\sum_{c \in C(v)} \operatorname{pairStumpFlow}_{vc} > 0
\right)
$$

$$
\forall v \in V, \quad
\operatorname{needBloom}_v = \sum_{t \in T_R} p_{vt}
$$

$$
\forall v \in V, \quad
\operatorname{hasClearing}_v = \sum_{t \in T_L} p_{vt}
$$

$$
\forall u \in V, v \in N(u), \quad
\operatorname{roadLink}_{uv} \equiv
\left(\sum_{t \in T} p_{ut} \cdot \operatorname{roadEdge}(t,D(u,v)) = 1\right)
\land
\left(\sum_{t \in T} p_{vt} \cdot \operatorname{roadEdge}(t,D(v,u)) = 1\right)
$$

$$
\forall v \in V, \quad
\operatorname{needConnect}_v = \sum_{t \in T_C} p_{vt}
$$

$$
\forall u \in V, v \in N(u), \quad
\operatorname{connectLink}_{uv} \equiv a_{u,e(u,v)} > 0
$$

where $e(u,v)$ is the shared edge between adjacent grids $u$ and $v$.

### Auxiliary Variables

| Meaning                                                        | Notation                                   | Type             |
| :------------------------------------------------------------- | :----------------------------------------- | :--------------- |
| Whether grid $u$ is the bloom parent of grid $v$               | $\operatorname{isBloomParent}_{uv}$        | Binary variable  |
| Topological order of grid $v$ in the bloom forest              | $\operatorname{bloomOrder}_v$              | Integer variable |
| Bloom source id propagated to grid $v$                         | $\operatorname{bloomSource}_v$             | Integer variable |
| Whether grid $v$ acts as a bloom source                        | $\operatorname{asBloomSource}_v$           | Binary variable  |
| Whether grid $u$ is the connectivity parent of grid $v$        | $\operatorname{isConnectParent}_{uv}$      | Binary variable  |
| Topological order of grid $v$ in the connectivity forest       | $\operatorname{connectOrder}_v$            | Integer variable |
| Whether grid $v$ is an exit root in the connectivity forest    | $\operatorname{exitAsConnectSource}_v$     | Binary variable  |
| Whether grid $v$ is a clearing root in the connectivity forest | $\operatorname{clearingAsConnectSource}_v$ | Binary variable  |
| Whether the connectivity source of grid $v$ is an exit         | $\operatorname{isConnectSourceExit}_v$     | Binary variable  |

The notation $\operatorname{isParent}_{uv}$ always means that $u$ is the parent and $v$ is the child.

## Constraints

### Aligned Figures

#### Requirement

Figures on adjacent tiles must align.

#### Naive Formulation

If a grid selects tile $t$, then each adjacent grid can only select a compatible subset of tiles:

$$
\forall (u,v) \in E,\ t \in T, \quad
x_{ut} \le \sum_{t' \in \operatorname{subset}(T,t)} x_{vt'}
$$

This has two drawbacks:

- **Tight tile coupling**: adding a tile requires updating compatibility subsets for existing tiles.
- **Weak propagation**: subset inequalities are usually weaker than equality over shared structure.

#### Adopted Formulation

Flow conservation describes figure compatibility. Each side of the same edge must expose the same edge-flow code:

$$
\forall e \in E, \quad \operatorname{AllEqual}(F^E_e)
$$

To add a new tile type, only $\operatorname{edgeFlow}(t,d)$ and related tile parameters need to be defined.

### Paired Stumps

#### Requirement

Stump tiles must appear in matching pairs:

- The arrows of the two stumps point toward each other.
- Exactly one road tile lies between the matching stumps.

#### Adopted Formulation

Stump pairing is another flow-conservation rule, but the flow meets at a grid rather than across an edge. The key is to define sufficiently fine-grained flow sets. For example, one channel can contain only the left and right contributors to grid $v$, while another channel contains only the upper and lower contributors.

Matching stump arrows emit the same non-zero stump-flow code toward the road tile between them; non-participating directions emit zero. Therefore each stump-flow channel is conserved by equality:

$$
\forall v \in V,\ c \in C(v), \quad
\operatorname{AllEqual}(F^S_{vc})
$$

With this formulation, a positive channel represents one matched stump pair through grid $v$, and zero means no stump pair exists on that channel:

$$
\forall v \in V,\ c \in C(v), \quad
\operatorname{pairStumpFlow}_{vc} \equiv
\mathbf{1}\left(\sum_{s \in F^S_{vc}} s > 0\right)
$$

The center grid can be between at most one stump pair:

$$
\forall v \in V, \quad
\sum_{c \in C(v)} \operatorname{pairStumpFlow}_{vc}
\le 1
$$

If stump flow meets at a grid, that grid must be a road tile:

$$
\forall v \in V, \quad
\operatorname{hasStumpFlow}_v \le \sum_{t \in T_R} p_{vt}
$$

In implementation, each $F^S_{vc}$ should include exactly the contributors that are allowed to match each other. This preserves the same flow-conservation idea used by edge alignment while avoiding a coarse set that mixes unrelated directions.

For boundary cases, avoid singleton flow sets: either omit channels that cannot form a pair, or include fixed zero contributors for missing sides so that an unmatched stump cannot satisfy conservation vacuously.

### Rooted Forest Template

Bloom and connectivity both use the same rooted-forest pattern. The tree structure is only the carrier; the modeled rule usually also needs a property to be grounded at roots and transmitted along parent-child edges.

For an active node expression $A_v$, a root expression or variable $R_v$, a parent variable $P_{uv}$, and a link expression $L_{uv}$:

$$
\forall v \in V, \quad
A_v = R_v + \sum_{u \in N(v)} P_{uv}
$$

Each active node is either a root or chooses exactly one parent. Inactive nodes choose neither.

$$
\forall u \in V,\ v \in N(u), \quad
P_{uv} \le A_u,\quad
P_{uv} \le A_v,\quad
P_{uv} \le L_{uv}
$$

Because $P_{uv}$ means "$u$ is the parent of $v$", the parent must have a smaller topological order:

$$
\forall u \in V,\ v \in N(u), \quad
P_{uv} \rightarrow \operatorname{order}_u + 1 \le \operatorname{order}_v
$$

The order constraint removes parent cycles. Without it, a cycle of non-root nodes could satisfy the parent equations without being grounded at a real source.

If the rule transmits a property $Q_v$, the root defines the ground truth for that property:

$$
\forall v \in V, \quad
R_v \rightarrow Q_v = \operatorname{rootValue}_v
$$

The parent-child relation transmits the same property:

$$
\forall u \in V,\ v \in N(u), \quad
P_{uv} \rightarrow Q_u = Q_v
$$

For some mechanics, parent propagation is still not enough because parent variables are auxiliary. Given the same placement, changing $P_{uv}$ can change which rooted tree a node appears to belong to. To prevent a node or link from being compatible with multiple conflicting sources, every possible transmission edge must carry the same property:

$$
\forall u \in V,\ v \in N(u), \quad
A_u \land A_v \land L_{uv} \rightarrow Q_u = Q_v
$$

This constraint is about possible membership, not only the selected parent tree. In the game, its bloom interpretation is: a road tile cannot connect to multiple bloom sources.

### Bloom

#### Requirement

Every road tile must bloom. A road tile blooms if it is:

- between a matching stump pair, which makes it a bloom source; or
- road-connected to another blooming road tile.

A road-connected component cannot contain multiple bloom sources.

#### Adopted Formulation

Use the rooted-forest template with:

$$
A_v = \operatorname{needBloom}_v
$$

$$
R_v = \operatorname{asBloomSource}_v
$$

$$
P_{uv} = \operatorname{isBloomParent}_{uv}
$$

$$
L_{uv} = \operatorname{roadLink}_{uv}
$$

Each road tile is either a selected bloom source or has one blooming parent:

$$
\forall v \in V, \quad
\operatorname{needBloom}_v =
\operatorname{asBloomSource}_v +
\sum_{u \in N(v)} \operatorname{isBloomParent}_{uv}
$$

Every matched stump pair is intrinsically a bloom source:

$$
\forall v \in V, \quad
\operatorname{asBloomSource}_v =
\operatorname{hasStumpFlow}_v
$$

This equality is required by the game semantics. If two matched stump pairs are connected by the same road network, both pairs are active bloom sources; the solver must not be allowed to turn one source off through an auxiliary variable.

Parent selection is only allowed along road connections:

$$
\forall u \in V,\ v \in N(u), \quad
\operatorname{isBloomParent}_{uv}
\le \operatorname{needBloom}_u
$$

$$
\forall u \in V,\ v \in N(u), \quad
\operatorname{isBloomParent}_{uv}
\le \operatorname{needBloom}_v
$$

$$
\forall u \in V,\ v \in N(u), \quad
\operatorname{isBloomParent}_{uv}
\le \operatorname{roadLink}_{uv}
$$

Bloom source labels are grounded at selected bloom sources and propagated through parent links:

$$
\forall v \in V, \quad
\operatorname{asBloomSource}_v \rightarrow
\operatorname{bloomSource}_v = \operatorname{id}(v)
$$

$$
\forall u \in V,\ v \in N(u), \quad
\operatorname{isBloomParent}_{uv} \rightarrow
\operatorname{bloomSource}_u = \operatorname{bloomSource}_v
$$

Cycles are forbidden by the bloom order:

$$
\forall u \in V,\ v \in N(u), \quad
\operatorname{isBloomParent}_{uv} \rightarrow
\operatorname{bloomOrder}_u + 1 \le \operatorname{bloomOrder}_v
$$

All possible road-transmission edges must carry the same bloom source:

$$
\forall u \in V,\ v \in N(u), \quad
\operatorname{needBloom}_u \land
\operatorname{needBloom}_v \land
\operatorname{roadLink}_{uv}
\rightarrow
\operatorname{bloomSource}_u = \operatorname{bloomSource}_v
$$

The last constraint is the key guardrail for the bloom model. Given a fixed placement, the parent variables can often be changed to attach a road tile to different rooted trees. Requiring every possible road-transmission edge to carry the same source removes that ambiguity: a road tile cannot be compatible with multiple bloom sources. Zero sources are still rejected by the parent/root equation, and two matched stump pairs connected through the same road network would force two different source ids to be equal.

## Optimization Goals

### Max Connectivity

This goal prefers fewer disconnected figure components. The formulation below treats road components as exit-rooted components and counts how many exit roots are needed.

Use the rooted-forest template with:

$$
A_v = \operatorname{needConnect}_v
$$

$$
R_v =
\operatorname{exitAsConnectSource}_v +
\operatorname{clearingAsConnectSource}_v
$$

$$
P_{uv} = \operatorname{isConnectParent}_{uv}
$$

$$
L_{uv} = \operatorname{connectLink}_{uv}
$$

Each active connectivity node is either a root or has one parent:

$$
\forall v \in V, \quad
\operatorname{needConnect}_v =
\operatorname{exitAsConnectSource}_v +
\operatorname{clearingAsConnectSource}_v +
\sum_{u \in N(v)} \operatorname{isConnectParent}_{uv}
$$

Only exits can be exit roots:

$$
\forall v \in V, \quad
\operatorname{exitAsConnectSource}_v \le \operatorname{isExit}(v)
$$

Only clearings can be clearing roots:

$$
\forall v \in V, \quad
\operatorname{clearingAsConnectSource}_v \le
\operatorname{hasClearing}_v
$$

Parent selection is only allowed through connected figures:

$$
\forall u \in V,\ v \in N(u), \quad
\operatorname{isConnectParent}_{uv}
\le \operatorname{needConnect}_u
$$

$$
\forall u \in V,\ v \in N(u), \quad
\operatorname{isConnectParent}_{uv}
\le \operatorname{needConnect}_v
$$

$$
\forall u \in V,\ v \in N(u), \quad
\operatorname{isConnectParent}_{uv}
\le \operatorname{connectLink}_{uv}
$$

Root type is propagated through the forest:

$$
\forall v \in V, \quad
\operatorname{exitAsConnectSource}_v
\rightarrow
\operatorname{isConnectSourceExit}_v = 1
$$

$$
\forall v \in V, \quad
\operatorname{clearingAsConnectSource}_v
\rightarrow
\operatorname{isConnectSourceExit}_v = 0
$$

$$
\forall u \in V,\ v \in N(u), \quad
\operatorname{isConnectParent}_{uv}
\rightarrow
\operatorname{isConnectSourceExit}_u =
\operatorname{isConnectSourceExit}_v
$$

Cycles are forbidden by the connectivity order:

$$
\forall u \in V,\ v \in N(u), \quad
\operatorname{isConnectParent}_{uv}
\rightarrow
\operatorname{connectOrder}_u + 1 \le
\operatorname{connectOrder}_v
$$

All active nodes connected by a valid figure link must agree on whether their component is exit-rooted:

$$
\forall u \in V,\ v \in N(u), \quad
\operatorname{needConnect}_u \land
\operatorname{needConnect}_v \land
\operatorname{connectLink}_{uv}
\rightarrow
\operatorname{isConnectSourceExit}_u =
\operatorname{isConnectSourceExit}_v
$$

If road components must be exit-rooted, add:

$$
\forall v \in V, \quad
\sum_{t \in T_R} p_{vt} = 1
\rightarrow
\operatorname{isConnectSourceExit}_v = 1
$$

The connectivity score is the number of exit-rooted components:

$$
\operatorname{connectivityScore} =
\sum_{v \in V} \operatorname{exitAsConnectSource}_v
$$

Max Connectivity minimizes this score.

Modeling note: this objective minimizes the number of exit-rooted components. If the intended metric later becomes "maximize the number of road tiles connected to exits", then unconnected road components should remain feasible and a separate expression such as $\sum_v \operatorname{connectedRoad}_v$ should be maximized instead.

### Max Density

The density score is the number of placed tiles in originally empty grids:

$$
\operatorname{densityScore} =
\sum_{v \in \hat{V},\ t \in T} x_{vt}
$$

Max Density maximizes this score.

## Cascading Optimization

When multiple optimization goals are enabled, apply them lexicographically:

1. Solve and optimize the first enabled goal.
2. Fix that goal's optimum value as an additional constraint.
3. Optimize the next enabled goal.
4. Repeat until all enabled goals are fixed.

This preserves priority order while still allowing later goals to refine the solution set.

## No-Good Cuts for Placement Enumeration

The model uses auxiliary variables such as parents, orders, and source labels. Standard solution enumeration may therefore return the same tile placement multiple times with different auxiliary assignments.

To enumerate unique placements, cut only the binary placement variables. Given binary variables $(b_1,\dots,b_n)$ and a found assignment $(y_1,\dots,y_n)$:

$$
\sum_i
\left[
\mathbf{1}(y_i = 1)b_i +
\mathbf{1}(y_i = 0)(1-b_i)
\right]
\le n - 1
$$

For placement enumeration, use $b_i \in \{x_{vt} \mid v \in \hat{V},\ t \in T\}$.

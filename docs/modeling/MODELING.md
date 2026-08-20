# Constraint Programming Modeling

This document explains the modeling ideas behind the Tiling Forest solver. It is written as a guided tour first and a formula reference second.

The code is still the source of truth for implementation details. The goal here is to make the main ideas readable: what each puzzle mechanic means, why it is modeled in a particular way, and which variables are introduced only when they are needed.

## The Puzzle Region

The solver works on a selected region of the larger game map. A grid in that region can be one of two kinds:

- **Empty grid**: the solver may choose at most one tile from the tile pool.
- **Pre-placed grid**: the tile type is already known, but the solver may still decide whether this grid is active in the current local model.

That second point is important. A puzzle region in the game can be only a local window into a larger map. Some pre-placed tiles may not be connectable yet from the perspective of this local region. If every pre-placed tile were forced active, flow-conservation rules could make early or partial regions infeasible for the wrong reason.

So pre-placed grids are represented by activation variables. Their tile type is fixed, but their flow can be switched off unless another rule forces activation. Stump tiles are the main exception: when the paired-stump rule is enabled, pre-placed stumps must be active.

The solver also derives a set of **exits**. A non-unexplored pre-placed tile is an exit if it has a positive outgoing figure flow toward a grid outside the modeled region. If no such exit exists, the model falls back to treating every grid that is not explicitly marked unexplored as an exit. This keeps closed regions usable by the connectivity model.

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

The exact integer values used by the code are implementation details. What matters for the model is that each tile can answer a few local questions:

- What figure-flow code does this tile expose on each edge?
- Does this tile contain a road?
- Does this tile contain a clearing?
- Does this tile emit stump-flow toward a neighboring grid?

Those answers are enough to build the constraints below.

## Modeling Toolkit

The solver uses two recurring techniques.

**Flow conservation** is used when local shapes must match. Instead of writing pairwise compatibility lists for every tile combination, each tile side emits a small code. Compatible neighboring sides expose equal codes.

This is used for:

- aligned figures across shared edges;
- paired stumps that meet at the grid between them.

**Rooted forests** are used when something must be connected to a source. Each active node either becomes a root or chooses exactly one parent. A topological order prevents parent cycles, so every active node is grounded in a real source.

This is used for:

- bloom propagation through roads;
- connectivity scoring across roads and clearings.

These two techniques keep tile definitions local. Adding a tile usually means updating the tile-flow tables, not rebuilding every rule.

## Placement and Activation

For an empty grid, the solver creates one binary decision for each tile in the tile pool. At most one of those decisions can be true.

For a pre-placed grid, the solver creates one binary activation variable for the known tile. If the variable is true, the grid contributes that tile's flows to the model. If it is false, the grid is silent for this local solve.

This is why the internal expression for "tile `t` is active on grid `v`" is more general than a normal placement variable. For empty grids it means "the solver selected this tile"; for pre-placed grids it means "the known tile is active in the current region."

## Aligned Figures

### Game Meaning

Figures on adjacent tiles must align. If a road, clearing edge, or mixed figure reaches a shared edge, the neighboring tile must expose the same compatible figure on its side of that edge.

### Modeling Idea

Each tile emits an edge-flow code in each direction. Empty sides emit zero. Roads emit the road code. Clearing edges emit clearing codes that preserve their orientation.

For each shared edge, the model collects the flow values contributed by the grids touching that edge. When the aligned-figures constraint is enabled, all collected values must be equal.

This is the core trick: the solver does not need a compatibility matrix such as "tile A can touch tile B in direction east." It only needs local flow codes.

### Variables Introduced

No dedicated decision variable is needed for this rule. The edge-flow values are expressions derived from placement or activation variables.

## Paired Stumps

### Game Meaning

Two stump tiles form a pair when their arrows point toward each other with exactly one road tile between them.

### Modeling Idea

This is also flow conservation, but the flow meets at the center grid instead of across a shared edge.

The model uses grid-centered channels:

- one horizontal channel receives stump-flow from the west and east neighbors;
- one vertical channel receives stump-flow from the north and south neighbors.

Matching stump arrows emit the same non-zero stump-flow code toward the center grid. Non-participating directions emit zero. When a channel has at least two contributors, all contributors in that channel must be equal.

Singleton channels are ignored. A single stump contribution at a boundary cannot form a pair by itself, so there is no useful conservation constraint to add for that channel.

When the paired-stump rule is enabled, any grid reached by stump-flow must be active as a road tile. The current implementation does not impose a separate "at most one stump pair through a center grid" rule.

### Variables Introduced

The model introduces `hasStumpFlow(v)`, a boolean expression telling whether any stump-flow reaches grid `v`. It is used both by the stump rule itself and by bloom, because a road between matched stumps becomes a bloom source.

## Rooted Forests

Bloom and connectivity both need the same shape of reasoning: an active node must either be a source or be connected back to a source.

The model represents this as a directed forest. For each active grid `v`, the solver chooses one of two possibilities:

- `v` is a root source;
- `v` has one parent `u`.

A parent relation is allowed only when the parent grid is active, the child grid is active, and the parent has the right one-way link toward the child. The parent does not need to check the child's reverse link. Reverse compatibility belongs to the figure-alignment rule, which can be enabled independently.

The parent relation is auxiliary, so a placement may admit many different parent forests. To keep the forest meaningful, each parent must have a smaller topological order than its child. This removes cycles of parent pointers.

Some forests also propagate a source property. Bloom propagates the id of the bloom source. Connectivity propagates whether the chosen root is an exit. When a possible transmission edge exists, the implementation can require both sides to agree on that property, not only when the edge is selected as the parent edge.

## Bloom

### Game Meaning

Every active road tile must bloom.

A road tile can bloom in three ways:

- it lies between a matched stump pair;
- it is a pre-placed blooming tile that can act as an external bloom source for this local region;
- it receives bloom through road-flow from a blooming parent road.

This external-source case exists because the modeled region may be only part of the full map. Bloom may have entered the current puzzle from outside.

### Modeling Idea

Bloom uses the rooted-forest template. The active nodes are road tiles. A road tile is valid if it is a bloom source or if it chooses one bloom parent.

There are two kinds of bloom source in the implementation:

- `selfAsBloomingSource`, for externally blooming pre-placed grids;
- `stumpAsBloomingSource`, derived from `hasStumpFlow`.

An externally blooming grid can act as a local source. If such a grid is also an exit, the implementation treats that external source as mandatory.

Those source terms are both part of the root count for the bloom equation. A road tile must account for exactly one reason to bloom: external source, stump source, or one selected parent.

The forest also propagates a `bloomSourceId`. When a grid is a bloom source, its source id is its own grid id. Parent-child bloom links copy the same source id from parent to child.

The implementation also checks every possible bloom-parent edge and requires both sides to carry the same source id. This prevents the same road network from being compatible with multiple different bloom sources just because the auxiliary parent choices changed.

### Variables Introduced

Bloom introduces:

- `isBloomParent(u, v)`: whether `u` is the bloom parent of `v`;
- `canBloomParent(u, v)`: whether the active placement gives `u` a road-flow link toward `v`;
- `bloomOrder(v)`: topological order used to prevent parent cycles;
- `bloomSourceId(v)`: the id of the bloom source propagated to `v`;
- `selfAsBloomingSource(v)`: whether `v` uses its pre-placed blooming status as a local source.

## Connectivity

### Game Meaning

Connectivity is an optimization concept, not the same thing as a hard road-exit rule.

The solver prefers fewer disconnected active figure components. A component can have a root anywhere, because "being connected" by itself does not say that an internal cycle or internal component is invalid.

The optional `ROAD_MUST_EXIT` constraint adds the stricter game meaning: active road tiles must belong to a component whose root is an exit.

### Modeling Idea

Connectivity also uses the rooted-forest template. The active nodes are tiles that contain roads or clearings. A parent link is allowed when the parent has a positive figure-flow code toward the child.

Every active connectivity node either becomes `asConnectSource` or selects one parent. The `MAX_CONNECTIVITY` goal minimizes the number of `asConnectSource` roots, which prefers fewer connected components.

Each root also determines whether its component is exit-rooted. If a root is an exit grid, its propagated `isSourceExit` value is true; otherwise it is false. Parent links propagate this value through the forest.

When `ROAD_MUST_EXIT` is enabled, each active road tile is constrained to have `isSourceExit = true`. This keeps the base connectivity model flexible while letting stages opt into stricter road-exit behavior.

### Variables Introduced

Connectivity introduces:

- `isConnectParent(u, v)`: whether `u` is the connectivity parent of `v`;
- `connectOrder(v)`: topological order used to prevent parent cycles;
- `asConnectSource(v)`: whether `v` is a connectivity root;
- `isSourceExit(v)`: whether `v`'s connectivity root is an exit.

## Optimization Goals

Goals are applied in order. The solver optimizes the first enabled goal, fixes its optimum value as a constraint, then optimizes the next goal. This gives lexicographic behavior without needing a weighted objective.

### Max Connectivity

Despite the name, this goal is implemented as a minimization: minimize the number of connectivity roots. Fewer roots means fewer disconnected active figure components.

### Max Density

This goal maximizes the number of active placement variables, so the solver prefers filling more empty grids and activating more compatible known tiles.

### Min Unexplored

The current expression counts unexplored pre-placed grids whose propagated connectivity source is an exit, and the solver maximizes that count.

Operationally, this goal prefers solutions where unexplored boundary or frontier tiles are attached to exit-rooted connectivity structure.

## Enumerating Placements

The model has many auxiliary variables: parent choices, topological orders, source ids, and source flags. Two solver assignments can differ only in those auxiliary variables while representing the same tile placement.

To avoid returning duplicates, enumeration cuts only placement and activation variables. After a solution is found, the solver adds a no-good cut that forbids exactly that binary placement pattern, while leaving auxiliary variables out of the cut.

## Formal Reference

This section collects the compact mathematical version of the model. It is meant for checking details after reading the narrative sections above.

### Sets and Parameters

| Meaning                                      | Notation                        |
| :------------------------------------------- | :------------------------------ |
| All grids in the modeled region              | $V$                             |
| Empty grids                                  | $\hat{V}$                       |
| Pre-placed grids                             | $\bar{V}$                       |
| Cardinal directions                          | $D$                             |
| Neighbors of grid $v$                        | $N(v)$                          |
| Shared edge between adjacent grids $u,v$     | $e(u,v)$                        |
| Stump-flow channels centered at grid $v$     | $C(v)$                          |
| Contributors to channel $c$ centered at $v$  | $N_c(v)$                        |
| Unique grid id                               | $\operatorname{id}(v)$          |
| Tile pool for empty grids                    | $T$                             |
| Road tile types                              | $T_R$                           |
| Clearing tile types                          | $T_L$                           |
| Connectable tile types                       | $T_C = T_R \cup T_L$            |
| Known tile on pre-placed grid $v$            | $\tau(v)$                       |
| Whether grid $v$ is an exit                  | $\operatorname{isExit}(v)$      |
| Edge-flow code of tile $t$ in direction $d$  | $\operatorname{edgeFlow}(t,d)$  |
| Stump-flow code of tile $t$ in direction $d$ | $\operatorname{stumpFlow}(t,d)$ |

### Placement and Activation

For an empty grid:

$$
x_{vt} \in \{0,1\}, \quad v \in \hat{V}, t \in T
$$

For a pre-placed grid:

$$
y_v \in \{0,1\}, \quad v \in \bar{V}
$$

The unified active-placement expression is:

$$
p_{vt} =
\begin{cases}
x_{vt}, & v \in \hat{V} \\
y_v, & v \in \bar{V}, t = \tau(v) \\
0, & v \in \bar{V}, t \ne \tau(v)
\end{cases}
$$

At most one tile can be selected or activated per grid:

$$
\forall v \in V, \quad \sum_t p_{vt} \le 1
$$

When paired stumps are enabled, pre-placed stump activations are required:

$$
\forall v \in \bar{V}, \tau(v) \in T_{\text{stump}}, \quad y_v = 1
$$

### Derived Expressions

The edge-flow shown by grid $v$ toward neighbor direction $d$ is:

$$
a_{v,d} = \sum_t p_{vt} \cdot \operatorname{edgeFlow}(t,d)
$$

The stump-flow contributed by grid $u$ toward adjacent grid $v$ is:

$$
s_{u,v} = \sum_t p_{ut} \cdot \operatorname{stumpFlow}(t,D(u,v))
$$

Road, clearing, bloom, and connectivity activity are:

$$
\operatorname{isRoad}_v = \sum_{t \in T_R} p_{vt}
$$

$$
\operatorname{isClearing}_v = \sum_{t \in T_L} p_{vt}
$$

$$
\operatorname{needBloom}_v = \operatorname{isRoad}_v
$$

$$
\operatorname{needConnect}_v = \sum_{t \in T_C} p_{vt}
$$

### Aligned Figures

For each shared edge, collect the flow values from all modeled grids incident to that edge:

$$
F^E_e = \{a_{v,D(v,e)} \mid v \in V, e \in E(v)\}
$$

When aligned figures are enabled:

$$
\forall e, |F^E_e| \ge 2, \quad \operatorname{AllEqual}(F^E_e)
$$

### Paired Stumps

For each grid-centered stump channel:

$$
F^S_{v,c} = \{s_{u,v} \mid u \in N_c(v)\}
$$

When paired stumps are enabled:

$$
\forall v,c, |F^S_{v,c}| \ge 2, \quad \operatorname{AllEqual}(F^S_{v,c})
$$

The implementation defines:

$$
\operatorname{hasStumpFlow}_v \equiv
\left(\sum_{c \in C(v)} \sum_{s \in F^S_{v,c}} s > 0\right)
$$

and requires:

$$
\forall v, \quad \operatorname{hasStumpFlow}_v \le \operatorname{isRoad}_v
$$

### Rooted Forest Template

For an active expression $A_v$, a root expression $R_v$, parent variable $P_{uv}$, and one-way link expression $L_{uv}$:

$$
\forall v, \quad A_v = R_v + \sum_{u \in N(v)} P_{uv}
$$

$$
\forall u,v, \quad P_{uv} \le A_u,\quad P_{uv} \le A_v,\quad P_{uv} \le L_{uv}
$$

Topological order prevents cycles:

$$
\forall u,v, \quad P_{uv} \rightarrow \operatorname{order}_u + 1 \le \operatorname{order}_v
$$

If a source property $Q_v$ is propagated:

$$
P_{uv} \rightarrow Q_u = Q_v
$$

### Bloom

Bloom uses:

$$
A_v = \operatorname{needBloom}_v
$$

$$
R_v = \operatorname{selfAsBloomingSource}_v + \operatorname{hasStumpFlow}_v
$$

External bloom sources are constrained by pre-placed bloom status:

$$
\operatorname{selfAsBloomingSource}_v \le \operatorname{isBlooming}(v)
$$

If a blooming grid is also an exit, the implementation fixes it as an external source:

$$
\operatorname{isBlooming}(v) \land \operatorname{isExit}(v)
\rightarrow
\operatorname{selfAsBloomingSource}_v = 1
$$

The one-way bloom link is true when parent `u` and child `v` are both active roads and `u` has road-flow toward `v`:

$$
\operatorname{canBloomParent}_{uv}
\equiv
\operatorname{needBloom}_u
\land
\operatorname{needBloom}_v
\land
a_{u,D(u,v)} = \operatorname{ROAD\_FLOW}
$$

Each active road has exactly one bloom reason:

$$
\operatorname{needBloom}_v =
\operatorname{selfAsBloomingSource}_v
+ \operatorname{hasStumpFlow}_v
+ \sum_{u \in N(v)} \operatorname{isBloomParent}_{uv}
$$

Bloom source ids are grounded at sources:

$$
\operatorname{selfAsBloomingSource}_v \lor \operatorname{hasStumpFlow}_v
\rightarrow
\operatorname{bloomSourceId}_v = \operatorname{id}(v)
$$

Selected parents propagate the same source id:

$$
\operatorname{isBloomParent}_{uv}
\rightarrow
\operatorname{bloomSourceId}_u = \operatorname{bloomSourceId}_v
$$

Every possible bloom-parent edge also carries the same source id:

$$
\operatorname{canBloomParent}_{uv}
\rightarrow
\operatorname{bloomSourceId}_u = \operatorname{bloomSourceId}_v
$$

### Connectivity

Connectivity uses:

$$
A_v = \operatorname{needConnect}_v
$$

$$
R_v = \operatorname{asConnectSource}_v
$$

The one-way connectivity link is true when parent `u` has positive figure-flow toward child `v`:

$$
\operatorname{connectLink}_{uv} \equiv a_{u,D(u,v)} > 0
$$

Each active connectable grid is either a root or has one parent:

$$
\operatorname{needConnect}_v =
\operatorname{asConnectSource}_v
+ \sum_{u \in N(v)} \operatorname{isConnectParent}_{uv}
$$

A root determines whether the component is exit-rooted:

$$
\operatorname{asConnectSource}_v
\rightarrow
\operatorname{isSourceExit}_v = \operatorname{isExit}(v)
$$

Parents propagate that property:

$$
\operatorname{isConnectParent}_{uv}
\rightarrow
\operatorname{isSourceExit}_u = \operatorname{isSourceExit}_v
$$

The optional road-exit constraint is:

$$
\operatorname{isRoad}_v \le \operatorname{isSourceExit}_v
$$

### Objective Expressions

Max connectivity minimizes root count:

$$
\operatorname{connectivityScore}
=
\sum_{v \in V} \operatorname{asConnectSource}_v
$$

Max density maximizes active placement:

$$
\operatorname{densityScore}
=
\sum_{v \in V} \sum_t p_{vt}
$$

`MIN_UNEXPLORED` currently maximizes:

$$
\operatorname{exitedUnexploreScore}
=
\sum_{\substack{v \in \bar{V} \\
\operatorname{status}(v)=\operatorname{UNEXPLORED}}}
\operatorname{isSourceExit}_v
$$

### Cascading Optimization

For enabled goals $(g_1,\dots,g_k)$:

1. Optimize $g_i$.
2. Add a constraint fixing $g_i$ to its optimum value.
3. Continue with $g_{i+1}$.

### Placement No-Good Cuts

Given placement and activation variables $(b_1,\dots,b_n)$ and a found assignment $(y_1,\dots,y_n)$:

$$
\sum_i
\begin{cases}
b_i, & y_i = 1 \\
1 - b_i, & y_i = 0
\end{cases}
\le n - 1
$$

Only placement and activation variables are included in the cut. Auxiliary forest variables are intentionally ignored.

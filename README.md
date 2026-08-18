# Tiling Forest Solver

A GUI solver for the puzzle game _[Tiling Forest](https://store.steampowered.com/app/4213590/Tiling_Forest__Tiling_Town_Demo/)_ by _[muratsubo Games](https://store.steampowered.com/curator/45923456)_.

The project consists of two core components:

- **Backend Solver**: Receives puzzle regions and computes valid tile placements.
- **Frontend GUI**: Lets users draw maps, configure puzzle settings, and inspect solutions.

## Motivation & Disclaimer

- **Puzzle Assistant**: Designed as a helper tool when players get stuck, rather than a way to bypass the intended game experience.
- **Academic Practice**: A personal project for practicing mathematical modeling and constraint programming.
- _Disclaimer: This is an unofficial, non-commercial fan-made project. Please support the original developer by purchasing the game on Steam._

## Features

- **Modular Rule Configuration**: Rules can be toggled independently to match the mechanics unlocked in each stage:

  - **Aligned Figures**: Figures on adjacent tiles must align.
    - _Recommendation_: **Always keep enabled**, as this represents the fundamental challenge of the game.
  - **Paired Stumps**: Stump tiles must always appear in matching pairs.
    - _Recommendation_: Enable this once stump tiles are unlocked.
  - **Bloom**: Every road tile should bloom.
    - _Recommendation_: Enable this once all tile types are unlocked.

- **Cascading Optimization Goals**: Multiple valid solutions often exist under the same rules. You can toggle on/off and chain optimization goals to filter and prioritize results:

  - **Max Connectivity**: Prefer road networks with fewer disconnected components.
  - **Max Density**: Fill as many empty spaces as possible.

- **Multi-Region Joint Solving**: Since placement in one puzzle region can affect adjacent ones, the GUI allows selecting and solving multiple interconnected regions simultaneously.

- **Fine-Grained Solver Controls & Result Sorting**:
  - **Solver Limits**: Set constraints on solving time and the maximum number of returned solutions.
  - **Interactive Visualization**: Sort and inspect solutions directly in the GUI based on density or connectivity metrics.

## Under the Hood

The solver formulates the puzzle as a constraint programming model. For those interested, check out the [Full Modeling Details](docs/modeling/MODELING.md).

## Tech Stack & Dependencies

| Component    | Technology                                               | Role                                  | License                                                   |
| :----------- | :------------------------------------------------------- | :------------------------------------ | :-------------------------------------------------------- |
| **Frontend** | [PySide6 (Qt 6 & QML)](https://doc.qt.io/qtforpython-6/) | Cross-platform Modern GUI             | [GNU LGPLv3](https://www.gnu.org/licenses/lgpl-3.0.html)  |
| **Modeling** | [cpmpy](https://github.com/CPMpy/cpmpy)                  | Constraint Programming Modeling Layer | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) |
| **Solver**   | [OR-Tools (CP-SAT)](https://github.com/google/or-tools)  | Constraint Programming Solver         | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) |

## License

The project is licensed under the [MIT License](LICENSE).

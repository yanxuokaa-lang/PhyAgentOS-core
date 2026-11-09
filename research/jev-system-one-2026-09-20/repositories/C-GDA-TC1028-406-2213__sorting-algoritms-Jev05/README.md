[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/16dzzUIU)
[![Open in Codespaces](https://classroom.github.com/assets/launch-codespace-2972f46106e565e64193e422d61a12cf1da4916b45550586e14ef0a7c637dd04.svg)](https://classroom.github.com/open-in-codespaces?assignment_repo_id=20102162)
"# Sorting Algorithms Implementation Assignment

## Overview
In this assignment, you will implement six fundamental sorting algorithms in C++. This will help you understand different algorithmic approaches, their time complexities, and trade-offs.

## Learning Objectives
- Understand and implement classic sorting algorithms
- Analyze time and space complexity of different algorithms
- Compare performance characteristics empirically
- Practice C++ programming and algorithm implementation

## Algorithms to Implement

### 1. Bubble Sort
- **Complexity:** O(n²) time, O(1) space
- **Stability:** Stable
- **Description:** Repeatedly steps through the list, compares adjacent elements and swaps them if they're in wrong order

### 2. Selection Sort
- **Complexity:** O(n²) time, O(1) space
- **Stability:** Unstable (can be made stable)
- **Description:** Divides array into sorted and unsorted regions, repeatedly selects minimum from unsorted

### 3. Insertion Sort
- **Complexity:** O(n²) time (O(n) best case), O(1) space
- **Stability:** Stable
- **Description:** Builds sorted array one item at a time by inserting each element into its correct position

### 4. Merge Sort
- **Complexity:** O(n log n) time, O(n) space
- **Stability:** Stable
- **Description:** Divide-and-conquer algorithm that divides array into halves, sorts them, and merges

### 5. Quick Sort
- **Complexity:** O(n log n) average, O(n²) worst case, O(log n) space
- **Stability:** Unstable
- **Description:** Picks a pivot, partitions array around it, recursively sorts sub-arrays

### 6. Heap Sort
- **Complexity:** O(n log n) time, O(1) space
- **Stability:** Unstable
- **Description:** Uses a binary heap data structure to sort elements

## Project Structure
```
sorting-algorithms/
├── README.md               # This file
├── .gitignore             # Git ignore configuration
├── Makefile               # Build configuration
├── src/
│   ├── main.cpp           # Main program with menu
│   ├── sorting.h          # Function declarations
│   └── sorting.cpp        # YOUR IMPLEMENTATIONS GO HERE
├── tests/
│   ├── test_runner.cpp    # Test framework
│   └── test_cases.h       # Test cases
└── data/
    └── sample_data.txt    # Sample input data
```

## Getting Started

### Prerequisites
- C++ compiler (g++ or clang++)
- Make utility
- Git

### Setup Instructions

1. **Clone the repository** (if using GitHub Classroom, this will be your forked repository):
```bash
git clone <your-repository-url>
cd sorting-algorithms
```

2. **Verify project structure** - Ensure all files are present:
```bash
ls -la
# You should see: README.md, Makefile, src/, tests/, data/
```

3. **Build the project** for the first time:
```bash
make clean  # Clean any previous builds
make all    # Compile the main program
```

### Running the Project

#### Interactive Demo Program
```bash
./sorting_demo
```

This will launch an interactive menu where you can:
- Select different sorting algorithms
- Choose to input custom data or use sample data
- Visualize the sorting process
- Compare algorithm performance

#### Running Tests
```bash
make test
./test_runner
```

### What to Expect on First Run (Before Implementation)

When you first run the project **without implementing the algorithms**, here's what you'll see:

#### 1. Main Program (`./sorting_demo`)
```
========================================
     SORTING ALGORITHMS DEMO
========================================
1. Bubble Sort
2. Selection Sort
3. Insertion Sort
4. Merge Sort
5. Quick Sort
6. Heap Sort
7. Compare All Algorithms
8. Load Sample Data
0. Exit
========================================
Select option: 1

Enter array size: 5
Enter 5 elements: 3 1 4 1 5

Original array: [3, 1, 4, 1, 5]
Running Bubble Sort...
ERROR: Algorithm not implemented!
Sorted array: [3, 1, 4, 1, 5]  // Array remains unchanged
```

The program will:
- Display the menu correctly
- Accept input properly
- Show "ERROR: Algorithm not implemented!" or similar message
- Return the original unsorted array
- NOT crash (stub implementations prevent segmentation faults)

#### 2. Test Suite (`./test_runner`)
```
Running Sorting Algorithm Tests...
==================================

Testing Bubble Sort:
  ✗ Empty array test: FAILED
  ✗ Single element test: FAILED
  ✗ Already sorted test: FAILED
  ✗ Reverse sorted test: FAILED
  ✗ Random array test: FAILED
  ✗ Duplicates test: FAILED

Testing Selection Sort:
  ✗ Empty array test: FAILED
  ... (similar failures for all tests)

... (similar output for all 6 algorithms)

==================================
Test Summary:
  Total Tests: 36
  Passed: 0
  Failed: 36
  Success Rate: 0%
==================================
```

All tests will fail initially because the sorting functions are not implemented yet. This is expected!

### Troubleshooting First Run

If you encounter issues:

1. **Compilation Errors:**
```bash
# Check compiler version
g++ --version

# Try manual compilation if make fails
g++ -std=c++11 -o sorting_demo src/main.cpp src/sorting.cpp
```

2. **Permission Denied:**
```bash
# Make executable
chmod +x sorting_demo
chmod +x test_runner
```

3. **Missing Files:**
```bash
# Verify all source files exist
ls src/
# Should show: main.cpp, sorting.h, sorting.cpp
```

4. **Segmentation Fault:**
   - This shouldn't happen with stub implementations
   - If it does, check that sorting.cpp has empty function bodies that return without modifying the array

## Implementation Instructions

1. **Fork this repository** through GitHub Classroom
2. **Clone your fork** to your local machine
3. **Implement each sorting algorithm** in `src/sorting.cpp`
   - Look for `TODO` comments
   - Each function has a stub that needs implementation
   - Do NOT modify function signatures
4. **Test your implementations**
   - Use the provided test suite: `make test`
   - Test with the interactive demo: `./sorting_demo`
5. **Document your code** with clear comments
6. **Commit regularly** with meaningful commit messages

## Requirements

### Functional Requirements
- [ ] All six sorting algorithms must be correctly implemented
- [ ] Algorithms must sort arrays in ascending order
- [ ] Implementations must handle edge cases (empty arrays, single element, duplicates)
- [ ] All provided tests must pass

### Code Quality Requirements
- [ ] Clear, readable code with appropriate variable names
- [ ] Proper indentation and formatting
- [ ] Comments explaining complex logic
- [ ] No memory leaks or undefined behavior

### Analysis Requirements
Create a file `ANALYSIS.md` containing:
- Time complexity analysis for each algorithm (best, average, worst cases)
- Space complexity analysis
- Empirical performance comparison (run times on different input sizes)
- Discussion of when to use each algorithm

## Grading Rubric

| Component | Points | Description |
|-----------|--------|-------------|
| Bubble Sort | 10 | Correct implementation |
| Selection Sort | 10 | Correct implementation |
| Insertion Sort | 10 | Correct implementation |
| Merge Sort | 15 | Correct implementation |
| Quick Sort | 15 | Correct implementation |
| Heap Sort | 15 | Correct implementation |
| Test Cases | 10 | All tests passing |
| Code Quality | 10 | Clean, documented code |
| Analysis | 5 | Complexity analysis document |
| **Total** | **100** | |

## Testing Your Implementation

The test suite includes:
- Empty array test
- Single element test
- Already sorted array
- Reverse sorted array
- Random arrays of various sizes
- Arrays with duplicate elements

Run tests with:
```bash
make test
```

## Tips for Success

1. **Start Simple:** Implement bubble sort first to understand the structure
2. **Test Incrementally:** Test each algorithm as you implement it
3. **Use Helper Functions:** For merge sort and quick sort, implement helper functions
4. **Debug Systematically:** Use the provided print functions to visualize array states
5. **Compare Outputs:** Verify your results against expected sorted arrays

## Common Pitfalls to Avoid

- **Off-by-one errors:** Be careful with array bounds
- **Integer overflow:** Consider large array indices
- **Incorrect base cases:** Ensure recursive algorithms handle base cases
- **Memory management:** Properly allocate/deallocate dynamic memory in merge sort
- **Pivot selection:** In quick sort, consider different pivot strategies

## Submission

1. Ensure all algorithms are implemented and tests pass
2. Complete the `ANALYSIS.md` file
3. Commit and push all changes to your GitHub repository
4. Submit through GitHub Classroom before the deadline

## Academic Integrity

This is an individual assignment. You may:
- Consult course materials and textbooks
- Discuss general approaches with classmates
- Use online resources for understanding concepts

You may NOT:
- Copy code from other students or online sources
- Use AI tools to generate complete implementations
- Share your code with other students

## Questions?

If you have questions about the assignment:
1. Check the course discussion forum
2. Attend office hours
3. Email the instructor/TA

Good luck with your implementation!
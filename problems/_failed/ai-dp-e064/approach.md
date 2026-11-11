1. Use rerooting DP extended from standard tree minimum dominating set DP with 3 states per node.
2. Key insight: Building core at u equals forcing u into the dominating set, replacing c[u] with K.
3. Preprocess subtree DP values via post-order traversal, then compute parent-side contributions via pre-order traversal.
4. Time complexity O(n), space O(n), fits n=1e5 constraints.
5. Most unsure step: Correctly handling INF states to avoid overflow and invalid subtraction of INF values.

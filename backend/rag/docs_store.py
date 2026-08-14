from rag.base_store import BaseVectorStore

class DocsStore(BaseVectorStore):
    COLLECTION_NAME: str = "docs"

    def seed_builtins(self) -> int:
        """
        Seed the documentation store with helper snippets about FastAPI, pytest,
        python, and core DSA (data structures & algorithms) concepts.
        """
        docs = [
            # ---------------- FastAPI (existing) ----------------
            "FastAPI endpoint: To define a GET endpoint, use @app.get('/path'). Example:\n@app.get('/health')\nasync def health():\n    return {'status': 'ok'}",
            "FastAPI CORS: To enable CORS in FastAPI, add CORSMiddleware:\nfrom fastapi.middleware.cors import CORSMiddleware\napp.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])",
            "FastAPI StreamingResponse: Use StreamingResponse to stream data. Example:\nfrom fastapi.responses import StreamingResponse\nasync def event_stream():\n    yield 'data: hello\\n\\n'\nreturn StreamingResponse(event_stream(), media_type='text/event-stream')",
            "Pytest basics: Pytest runs tests in test_*.py or *_test.py. Test functions must start with test_. Example:\ndef test_addition():\n    assert 1 + 1 == 2",
            "Pytest async: To test async functions, use pytest-asyncio and mark the test with @pytest.mark.asyncio. Example:\n@pytest.mark.asyncio\nasync def test_async():\n    res = await async_func()\n    assert res is True",
            "Uvicorn: Run a FastAPI app using uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True) in the entrypoint file.",
            "SQLAlchemy connection: To create a SQLite engine and session, use:\nfrom sqlalchemy import create_engine\nfrom sqlalchemy.orm import sessionmaker\nengine = create_engine('sqlite:///test.db')\nSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)",
            "Pydantic Model: To define schemas with Pydantic for validation, use BaseModel. Example:\nfrom pydantic import BaseModel\nclass UserSchema(BaseModel):\n    id: int\n    username: str\n    email: str",

            # ---------------- FastAPI (new/missing concepts) ----------------
            "FastAPI Path & Query Params: Path params are declared in the route; query params are plain function args with defaults. Example:\n@app.get('/items/{item_id}')\nasync def read_item(item_id: int, q: str | None = None):\n    return {'item_id': item_id, 'q': q}",
            "FastAPI Request Body: Use a Pydantic model as a parameter to parse and validate the JSON body. Example:\n@app.post('/users')\nasync def create_user(user: UserSchema):\n    return user",
            "FastAPI Dependency Injection: Use Depends() to share reusable logic (e.g. DB sessions, auth). Example:\ndef get_db():\n    db = SessionLocal()\n    try:\n        yield db\n    finally:\n        db.close()\n\n@app.get('/users')\ndef list_users(db: Session = Depends(get_db)):\n    return db.query(User).all()",
            "FastAPI Response Model: Restrict/shape output fields using response_model. Example:\n@app.get('/users/{id}', response_model=UserOut)\nasync def get_user(id: int):\n    return db_user",
            "FastAPI Background Tasks: Run work after returning a response using BackgroundTasks. Example:\nfrom fastapi import BackgroundTasks\n@app.post('/notify')\nasync def notify(bg: BackgroundTasks):\n    bg.add_task(send_email, 'user@example.com')\n    return {'status': 'queued'}",
            "FastAPI WebSockets: Handle real-time bidirectional connections. Example:\n@app.websocket('/ws')\nasync def websocket_endpoint(ws: WebSocket):\n    await ws.accept()\n    while True:\n        data = await ws.receive_text()\n        await ws.send_text(f'echo: {data}')",
            "FastAPI Exception Handling: Use HTTPException for expected errors, or custom exception handlers. Example:\nfrom fastapi import HTTPException\n@app.get('/items/{id}')\nasync def get_item(id: int):\n    if id not in db:\n        raise HTTPException(status_code=404, detail='Item not found')",
            "FastAPI Custom Exception Handler: Register a handler for a custom exception class. Example:\n@app.exception_handler(MyError)\nasync def my_error_handler(request, exc):\n    return JSONResponse(status_code=400, content={'error': str(exc)})",
            "FastAPI Middleware: Run code before/after every request. Example:\n@app.middleware('http')\nasync def add_process_time(request, call_next):\n    response = await call_next(request)\n    response.headers['X-Process-Time'] = '1'\n    return response",
            "FastAPI File Upload: Accept uploaded files using UploadFile. Example:\nfrom fastapi import UploadFile, File\n@app.post('/upload')\nasync def upload(file: UploadFile = File(...)):\n    contents = await file.read()\n    return {'filename': file.filename}",
            "FastAPI OAuth2/JWT Auth: Use OAuth2PasswordBearer to secure endpoints. Example:\nfrom fastapi.security import OAuth2PasswordBearer\noauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')\n@app.get('/me')\nasync def read_me(token: str = Depends(oauth2_scheme)):\n    return decode_jwt(token)",
            "FastAPI APIRouter: Split routes into modules and include them in the main app. Example:\nfrom fastapi import APIRouter\nrouter = APIRouter(prefix='/users', tags=['users'])\n@router.get('/')\nasync def list_users(): ...\napp.include_router(router)",
            "FastAPI Settings/Config: Use pydantic-settings for env-based config. Example:\nfrom pydantic_settings import BaseSettings\nclass Settings(BaseSettings):\n    db_url: str\n    debug: bool = False\nsettings = Settings()",
            "FastAPI Testing: Use TestClient (from fastapi.testclient) to test endpoints synchronously. Example:\nfrom fastapi.testclient import TestClient\nclient = TestClient(app)\ndef test_health():\n    r = client.get('/health')\n    assert r.status_code == 200",
            "FastAPI Startup/Shutdown Events: Run logic on app lifecycle using lifespan context manager. Example:\nfrom contextlib import asynccontextmanager\n@asynccontextmanager\nasync def lifespan(app: FastAPI):\n    print('starting up')\n    yield\n    print('shutting down')\napp = FastAPI(lifespan=lifespan)",

            # ---------------- DSA: Complexity & Fundamentals ----------------
            "Big-O Cheat Sheet: O(1) constant, O(log n) logarithmic (binary search), O(n) linear (single loop), O(n log n) (efficient sorts: merge/quick/heap), O(n^2) quadratic (nested loops, bubble/insertion sort), O(2^n) exponential (naive recursive fibonacci/subsets), O(n!) factorial (permutations).",
            "Arrays Basics: Contiguous memory, O(1) index access, O(n) insert/delete (except at end). Example:\narr = [1, 2, 3]\narr.append(4)      # O(1) amortized\narr.insert(0, 0)   # O(n)\narr.pop()          # O(1)",
            "Strings Basics: Immutable in Python; use list/join for efficient building. Example:\nparts = []\nfor c in 'hello':\n    parts.append(c.upper())\nresult = ''.join(parts)  # avoids O(n^2) concatenation",
            "Two Pointers Technique: Use two indices moving toward/away from each other to solve array/string problems in O(n). Example (reverse array):\ndef reverse(arr):\n    l, r = 0, len(arr) - 1\n    while l < r:\n        arr[l], arr[r] = arr[r], arr[l]\n        l += 1\n        r -= 1",
            "Sliding Window: Maintain a window over a subarray/substring to solve max/min subarray problems in O(n). Example (max sum of size k):\ndef max_sum(arr, k):\n    window = sum(arr[:k])\n    best = window\n    for i in range(k, len(arr)):\n        window += arr[i] - arr[i - k]\n        best = max(best, window)\n    return best",

            # ---------------- DSA: Linked Lists ----------------
            "Singly Linked List: Nodes with value + next pointer. Example:\nclass Node:\n    def __init__(self, val):\n        self.val = val\n        self.next = None\n\ndef reverse_list(head):\n    prev = None\n    while head:\n        nxt = head.next\n        head.next = prev\n        prev = head\n        head = nxt\n    return prev",
            "Detect Cycle in Linked List (Floyd's Algorithm): Use slow/fast pointers; if they meet, a cycle exists. Example:\ndef has_cycle(head):\n    slow = fast = head\n    while fast and fast.next:\n        slow = slow.next\n        fast = fast.next.next\n        if slow is fast:\n            return True\n    return False",
            "Doubly Linked List: Nodes with value, next, and prev pointers, allowing O(1) removal given a node reference. Example:\nclass DNode:\n    def __init__(self, val):\n        self.val = val\n        self.prev = None\n        self.next = None",

            # ---------------- DSA: Stacks, Queues, Hashing ----------------
            "Stack (LIFO): Use a list with append/pop for O(1) push/pop. Example (valid parentheses):\ndef is_valid(s):\n    stack = []\n    pairs = {')': '(', ']': '[', '}': '{'}\n    for c in s:\n        if c in pairs:\n            if not stack or stack.pop() != pairs[c]:\n                return False\n        else:\n            stack.append(c)\n    return not stack",
            "Queue (FIFO): Use collections.deque for O(1) append/popleft. Example:\nfrom collections import deque\nq = deque()\nq.append(1)\nq.append(2)\nq.popleft()  # returns 1",
            "Hash Map / Set: O(1) average lookup, insert, delete. Example (two sum):\ndef two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i",
            "Priority Queue / Heap: Use heapq for a min-heap; negate values for a max-heap. Example:\nimport heapq\nheap = []\nheapq.heappush(heap, 3)\nheapq.heappush(heap, 1)\nheapq.heappop(heap)  # returns 1 (smallest)",
            "Union-Find (Disjoint Set Union): Efficiently tracks connected components with path compression + union by rank. Example:\nclass DSU:\n    def __init__(self, n):\n        self.parent = list(range(n))\n    def find(self, x):\n        if self.parent[x] != x:\n            self.parent[x] = self.find(self.parent[x])\n        return self.parent[x]\n    def union(self, a, b):\n        ra, rb = self.find(a), self.find(b)\n        if ra != rb:\n            self.parent[ra] = rb",

            # ---------------- DSA: Searching & Sorting ----------------
            "Binary Search: Requires sorted array; O(log n). Example:\ndef binary_search(arr, target):\n    lo, hi = 0, len(arr) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1",
            "Bubble Sort: O(n^2), simple, in-place. Example:\ndef bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(n - i - 1):\n            if arr[j] > arr[j + 1]:\n                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n    return arr",
            "Merge Sort: O(n log n), stable, divide-and-conquer. Example:\ndef merge_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    mid = len(arr) // 2\n    left, right = merge_sort(arr[:mid]), merge_sort(arr[mid:])\n    result, i, j = [], 0, 0\n    while i < len(left) and j < len(right):\n        if left[i] <= right[j]:\n            result.append(left[i]); i += 1\n        else:\n            result.append(right[j]); j += 1\n    return result + left[i:] + right[j:]",
            "Quick Sort: O(n log n) average, O(n^2) worst case, in-place partitioning. Example:\ndef quick_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    mid = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quick_sort(left) + mid + quick_sort(right)",

            # ---------------- DSA: Recursion & Backtracking ----------------
            "Recursion Basics: A function calling itself with a base case to prevent infinite recursion. Example:\ndef factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)",
            "Backtracking: Explore choices, undo (backtrack) when a path fails. Example (subsets):\ndef subsets(nums):\n    res = []\n    def backtrack(start, path):\n        res.append(path[:])\n        for i in range(start, len(nums)):\n            path.append(nums[i])\n            backtrack(i + 1, path)\n            path.pop()\n    backtrack(0, [])\n    return res",
            "Permutations (Backtracking): Generate all orderings of a list. Example:\ndef permute(nums):\n    res = []\n    def backtrack(path, remaining):\n        if not remaining:\n            res.append(path)\n            return\n        for i in range(len(remaining)):\n            backtrack(path + [remaining[i]], remaining[:i] + remaining[i+1:])\n    backtrack([], nums)\n    return res",

            # ---------------- DSA: Trees ----------------
            "Binary Tree Traversals: Inorder (L-Root-R), Preorder (Root-L-R), Postorder (L-R-Root). Example:\ndef inorder(node, res):\n    if node:\n        inorder(node.left, res)\n        res.append(node.val)\n        inorder(node.right, res)",
            "Binary Search Tree (BST): Left subtree < node < right subtree, giving O(log n) average search/insert. Example:\ndef insert(root, val):\n    if not root:\n        return TreeNode(val)\n    if val < root.val:\n        root.left = insert(root.left, val)\n    else:\n        root.right = insert(root.right, val)\n    return root",
            "Level-Order Traversal (BFS on Tree): Traverse a tree level by level using a queue. Example:\nfrom collections import deque\ndef level_order(root):\n    res, q = [], deque([root]) if root else deque()\n    while q:\n        node = q.popleft()\n        res.append(node.val)\n        if node.left: q.append(node.left)\n        if node.right: q.append(node.right)\n    return res",
            "Trie (Prefix Tree): Stores strings for efficient prefix search, O(L) per operation where L is word length. Example:\nclass TrieNode:\n    def __init__(self):\n        self.children = {}\n        self.is_end = False\n\nclass Trie:\n    def __init__(self):\n        self.root = TrieNode()\n    def insert(self, word):\n        node = self.root\n        for c in word:\n            node = node.children.setdefault(c, TrieNode())\n        node.is_end = True",

            # ---------------- DSA: Graphs ----------------
            "Graph Representation: Adjacency list is the most common form. Example:\ngraph = {\n    'A': ['B', 'C'],\n    'B': ['D'],\n    'C': ['D'],\n    'D': []\n}",
            "Breadth-First Search (BFS): Explores graph level by level using a queue; finds shortest path in unweighted graphs. Example:\nfrom collections import deque\ndef bfs(graph, start):\n    visited, q = {start}, deque([start])\n    order = []\n    while q:\n        node = q.popleft()\n        order.append(node)\n        for nb in graph[node]:\n            if nb not in visited:\n                visited.add(nb)\n                q.append(nb)\n    return order",
            "Depth-First Search (DFS): Explores as far as possible before backtracking; can be recursive or iterative with a stack. Example:\ndef dfs(graph, node, visited=None):\n    if visited is None:\n        visited = set()\n    visited.add(node)\n    for nb in graph[node]:\n        if nb not in visited:\n            dfs(graph, nb, visited)\n    return visited",
            "Dijkstra's Algorithm: Finds shortest paths from a source in a weighted graph with non-negative edges, using a min-heap. O((V+E) log V). Example:\nimport heapq\ndef dijkstra(graph, start):\n    dist = {start: 0}\n    pq = [(0, start)]\n    while pq:\n        d, node = heapq.heappop(pq)\n        if d > dist.get(node, float('inf')):\n            continue\n        for nb, w in graph[node]:\n            nd = d + w\n            if nd < dist.get(nb, float('inf')):\n                dist[nb] = nd\n                heapq.heappush(pq, (nd, nb))\n    return dist",
            "Topological Sort: Orders nodes in a DAG such that every edge points forward; used for task scheduling. Example (Kahn's algorithm):\nfrom collections import deque\ndef topo_sort(graph, indegree):\n    q = deque([n for n in graph if indegree[n] == 0])\n    order = []\n    while q:\n        node = q.popleft()\n        order.append(node)\n        for nb in graph[node]:\n            indegree[nb] -= 1\n            if indegree[nb] == 0:\n                q.append(nb)\n    return order",

            # ---------------- DSA: Dynamic Programming & Greedy ----------------
            "Dynamic Programming - Memoization (Top-Down): Cache results of subproblems to avoid recomputation. Example (Fibonacci):\nfrom functools import lru_cache\n@lru_cache(maxsize=None)\ndef fib(n):\n    if n <= 1:\n        return n\n    return fib(n - 1) + fib(n - 2)",
            "Dynamic Programming - Tabulation (Bottom-Up): Build a table iteratively from base cases. Example (0/1 Knapsack):\ndef knapsack(weights, values, capacity):\n    n = len(weights)\n    dp = [[0] * (capacity + 1) for _ in range(n + 1)]\n    for i in range(1, n + 1):\n        for w in range(capacity + 1):\n            dp[i][w] = dp[i-1][w]\n            if weights[i-1] <= w:\n                dp[i][w] = max(dp[i][w], dp[i-1][w-weights[i-1]] + values[i-1])\n    return dp[n][capacity]",
            "Longest Common Subsequence (LCS): Classic 2D DP problem. Example:\ndef lcs(a, b):\n    m, n = len(a), len(b)\n    dp = [[0]*(n+1) for _ in range(m+1)]\n    for i in range(1, m+1):\n        for j in range(1, n+1):\n            if a[i-1] == b[j-1]:\n                dp[i][j] = dp[i-1][j-1] + 1\n            else:\n                dp[i][j] = max(dp[i-1][j], dp[i][j-1])\n    return dp[m][n]",
            "Greedy Algorithms: Make the locally optimal choice at each step, hoping for a global optimum (works for problems with greedy-choice property). Example (activity selection / interval scheduling):\ndef max_activities(intervals):\n    intervals.sort(key=lambda x: x[1])\n    count, last_end = 0, float('-inf')\n    for start, end in intervals:\n        if start >= last_end:\n            count += 1\n            last_end = end\n    return count",
        ]

        metadatas = [
            {"source": "fastapi_docs", "topic": "fastapi_get", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_cors", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_streaming", "language": "python"},
            {"source": "pytest_docs", "topic": "pytest_basics", "language": "python"},
            {"source": "pytest_docs", "topic": "pytest_asyncio", "language": "python"},
            {"source": "uvicorn_docs", "topic": "uvicorn_run", "language": "python"},
            {"source": "sqlalchemy_docs", "topic": "sqlalchemy_sqlite", "language": "python"},
            {"source": "pydantic_docs", "topic": "pydantic_schema", "language": "python"},

            {"source": "fastapi_docs", "topic": "fastapi_path_query_params", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_request_body", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_dependency_injection", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_response_model", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_background_tasks", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_websockets", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_exception_handling", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_custom_exception_handler", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_middleware", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_file_upload", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_oauth2_jwt", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_api_router", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_settings_config", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_testing", "language": "python"},
            {"source": "fastapi_docs", "topic": "fastapi_lifespan_events", "language": "python"},

            {"source": "dsa_docs", "topic": "big_o_complexity", "language": "python"},
            {"source": "dsa_docs", "topic": "arrays_basics", "language": "python"},
            {"source": "dsa_docs", "topic": "strings_basics", "language": "python"},
            {"source": "dsa_docs", "topic": "two_pointers", "language": "python"},
            {"source": "dsa_docs", "topic": "sliding_window", "language": "python"},

            {"source": "dsa_docs", "topic": "singly_linked_list", "language": "python"},
            {"source": "dsa_docs", "topic": "linked_list_cycle", "language": "python"},
            {"source": "dsa_docs", "topic": "doubly_linked_list", "language": "python"},

            {"source": "dsa_docs", "topic": "stack", "language": "python"},
            {"source": "dsa_docs", "topic": "queue", "language": "python"},
            {"source": "dsa_docs", "topic": "hashmap_hashset", "language": "python"},
            {"source": "dsa_docs", "topic": "priority_queue_heap", "language": "python"},
            {"source": "dsa_docs", "topic": "union_find_dsu", "language": "python"},

            {"source": "dsa_docs", "topic": "binary_search", "language": "python"},
            {"source": "dsa_docs", "topic": "bubble_sort", "language": "python"},
            {"source": "dsa_docs", "topic": "merge_sort", "language": "python"},
            {"source": "dsa_docs", "topic": "quick_sort", "language": "python"},

            {"source": "dsa_docs", "topic": "recursion_basics", "language": "python"},
            {"source": "dsa_docs", "topic": "backtracking", "language": "python"},
            {"source": "dsa_docs", "topic": "permutations", "language": "python"},

            {"source": "dsa_docs", "topic": "binary_tree_traversals", "language": "python"},
            {"source": "dsa_docs", "topic": "binary_search_tree", "language": "python"},
            {"source": "dsa_docs", "topic": "tree_level_order_bfs", "language": "python"},
            {"source": "dsa_docs", "topic": "trie", "language": "python"},

            {"source": "dsa_docs", "topic": "graph_representation", "language": "python"},
            {"source": "dsa_docs", "topic": "graph_bfs", "language": "python"},
            {"source": "dsa_docs", "topic": "graph_dfs", "language": "python"},
            {"source": "dsa_docs", "topic": "dijkstra", "language": "python"},
            {"source": "dsa_docs", "topic": "topological_sort", "language": "python"},

            {"source": "dsa_docs", "topic": "dp_memoization", "language": "python"},
            {"source": "dsa_docs", "topic": "dp_tabulation_knapsack", "language": "python"},
            {"source": "dsa_docs", "topic": "lcs", "language": "python"},
            {"source": "dsa_docs", "topic": "greedy_algorithms", "language": "python"},
        ]

        ids = [f"doc_builtin_{i}" for i in range(len(docs))]

        # Add to the collection using the inherited add method
        self.add(docs, metadatas, ids)
        return len(docs)

# Data Analyst Agent Implementation Plan

## 📊 Current Architecture Understanding

### Backend Workflow (nidhi-tmp-backend/text2sql)
1. **SQL Generation**: User query to SQL
2. **SQL Execution**: Execute SQL query
3. **SQL Validation (optional)**: Validate results
4. **Response Generator (optional)**: Generate natural language response

### Frontend (nidhi-fi)
- Currently displays only text responses
- No tables or chart visualizations

---

## 🎯 Proposed Data Analyst Agent Plan

### Architecture Change
Insert a new step between SQL Execution and Natural Language Response:
1. SQL Generation
2. SQL Execution
3. **✨ DATA ANALYST AGENT (NEW) ✨**
4. Response Generator (Modified)

### Data Analyst Agent Responsibilities
The agent will:
1. Analyze the query intent and result structure
2. Determine optimal visualization format:
   - **Table**: List/detail queries ("show all accounts", "list transactions")
   - **Text Only**: Count/aggregate queries ("how many...", "what's my total...")
   - **Chart**: Trend/analytical queries ("spending last week", "transactions by category")
3. Transform data into visualization-ready format
4. Attach metadata for frontend rendering

### Implementation Plan

#### Backend Changes (nidhi-tmp-backend)
1. **Create Data Analyst Agent**
   - Location: `nidhi-tmp-backend/text2sql/agents/data_analyst_agent.py`
   - Functions:
     - Query classification (using pattern matching or lightweight LLM call)
     - Visualization type selection
     - Data transformation for charts/tables
2. **Create New Function**
   - Location: `nidhi-tmp-backend/text2sql/functions/data_analyzer.py`
   - Inherits from `BaseFunction`
   - Key methods:
     - `analyze_query_intent()`: Determine query type
     - `select_visualization()`: Choose table/chart/text
     - `prepare_chart_data()`: Format data for Chart.js/Recharts
     - `prepare_table_data()`: Format tabular data
3. **Modify LLM Agent Pipeline**
   - File: `nidhi-tmp-backend/text2sql/agents/llm_agent.py`
   - Add Step 3.5 (after execution, before response generation):
     ```python
     # Step 3: Execute SQL
     execution_result = self.get_function("sql_executor").run(...)
     # Step 3.5: Analyze data for visualization (NEW)
     analyst_input = {
         'user_query': user_query,
         'query_result': execution_result,
         'sql': sql_result['sql']
     }
     analyst_result = self.get_function("data_analyzer").run(analyst_input)
     # Step 4: Generate NL response (pass analyst result)
     response_input = {
         'user_query': user_query,
         'query_result': execution_result,
         'analyst_result': analyst_result, # NEW
         'validation_result': validation_result
     }

4. Update Response Models
  - File: nidhi-tmp-backend/app.py
  - Modify ChatQueryResponse:
  class ChatQueryResponse(BaseModel):
      # ... existing fields ...
      visualization: Optional[dict] = None  # NEW
      # visualization format:
      # {
      #   "type": "table" | "text" | "chart",
      #   "chart_type": "bar" | "line" | "pie" | null,
      #   "data": [...],  # Chart.js/Recharts compatible
      #   "config": {...}  # Chart configuration
      # }

  5. Install Required Libraries
  pandas>=2.0.0      # Data manipulation
  numpy>=1.24.0      # Numerical operations

  Frontend Changes (nidhi-fi)

  1. Install Charting Library
  npm install recharts
  npm install @types/recharts --save-dev

  2. Create Visualization Components
  - nidhi-fi/src/components/chat/TableView.tsx - Render data tables
  - nidhi-fi/src/components/chat/ChartView.tsx - Render charts (bar/line/pie)
  - nidhi-fi/src/components/chat/MessageContent.tsx - Orchestrate rendering

  3. Update Message Interface
  - File: nidhi-fi/src/pages/Chat.tsx
  interface Message {
    // ... existing fields ...
    visualization?: {
      type: 'table' | 'text' | 'chart';
      chart_type?: 'bar' | 'line' | 'pie';
      data: any[];
      config?: any;
    };
  }

  4. Modify Message Rendering
  - Display text, then visualization (if present)
  - Use conditional rendering based on visualization.type

  ---
  🧠 Data Analyst Agent Logic

  Query Classification Examples

  | User Query                            | Intent       | Visualization |
  |---------------------------------------|--------------|---------------|
  | "Show me all my accounts"             | Listing      | Table         |
  | "List transactions from last week"    | Listing      | Table         |
  | "How many transactions did I make?"   | Count        | Text only     |
  | "What's my total balance?"            | Aggregate    | Text only     |
  | "Transactions by category last month" | Analysis     | Bar Chart     |
  | "Spending trend this year"            | Trend        | Line Chart    |
  | "Breakdown of expenses"               | Distribution | Pie Chart     |

  Decision Tree Logic

  1. Check result structure:
     - Single value (count/sum) → TEXT
     - Multiple rows with 2-5 columns → TABLE
     - Multiple rows with time dimension → LINE CHART
     - Multiple rows with category + value → BAR/PIE CHART

  2. Check query keywords:
     - "show", "list", "all" → TABLE
     - "how many", "count", "total" → TEXT
     - "trend", "over time", "by month/week" → LINE CHART
     - "by category", "breakdown" → BAR/PIE CHART

  Sample Data Formats

  For Tables:
  {
    "type": "table",
    "data": [
      {"account_name": "Checking", "balance": 5000, "bank": "Chase"},
      {"account_name": "Savings", "balance": 10000, "bank": "Chase"}
    ]
  }

  For Bar Chart:
  {
    "type": "chart",
    "chart_type": "bar",
    "data": [
      {"category": "Food", "amount": 500},
      {"category": "Transport", "amount": 200}
    ],
    "config": {
      "xKey": "category",
      "yKey": "amount",
      "xLabel": "Category",
      "yLabel": "Amount ($)"
    }
  }

  For Line Chart:
  {
    "type": "chart",
    "chart_type": "line",
    "data": [
      {"date": "2024-01-01", "spending": 1200},
      {"date": "2024-01-02", "spending": 800}
    ],
    "config": {
      "xKey": "date",
      "yKey": "spending",
      "xLabel": "Date",
      "yLabel": "Spending ($)"
    }
  }

  ---
  📋 Implementation Checklist

  Phase 1: Backend Foundation

  - Create data_analyst_agent.py with query classification logic
  - Create data_analyzer.py function with visualization selection
  - Implement data transformation utilities (SQL results → chart format)
  - Add unit tests for query classification

  Phase 2: Backend Integration

  - Integrate Data Analyst Agent into LLM pipeline
  - Update ChatQueryResponse model with visualization field
  - Modify response generator to use analyst output
  - Test end-to-end workflow with sample queries

  Phase 3: Frontend Foundation

  - Install Recharts and dependencies
  - Create TableView component (responsive, sortable)
  - Create ChartView component (bar/line/pie support)
  - Create unified MessageContent component

  Phase 4: Frontend Integration

  - Update Message interface with visualization field
  - Modify Chat.tsx to render visualizations
  - Add loading states for chart rendering
  - Style components to match dark theme

  Phase 5: Testing & Refinement

  - Test with various query types
  - Refine classification rules based on edge cases
  - Add error handling for malformed data
  - Performance optimization (lazy loading for charts)

  ---
  🔍 Key Considerations

  1. Performance
  - Data Analyst Agent should be fast (< 200ms)
  - Use rule-based classification first, LLM only for ambiguous cases
  - Consider caching visualization metadata

  2. Scalability
  - Handle large result sets (pagination for tables)
  - Limit chart data points (aggregate if > 100 points)

  3. User Experience
  - Show text response + visualization together
  - Allow users to toggle between table/chart views
  - Export functionality (CSV for tables, PNG for charts)

  4. Fallback Strategy
  - If visualization fails → fallback to text + raw results
  - Log failures for improvement

  ---
  💡 Alternative Approaches

  Option 1: Lightweight (Current Proposal)
  - Rule-based classification
  - Minimal LLM usage
  - Fast, predictable

  Option 2: LLM-Heavy
  - Use GPT to decide visualization type
  - More flexible but slower and costly
  - Better for complex/ambiguous queries

  Option 3: Hybrid
  - Rule-based for common patterns
  - LLM for edge cases (10-20% of queries)
  - Balanced approach

  Recommendation: Start with Option 1, add Option 3 if needed.

  ---
  🎨 Sample Implementation Snippets

  Data Analyzer Function (Pseudo-code):
  class DataAnalyzer(BaseFunction):
      def run(self, input_data):
          query = input_data['user_query'].lower()
          results = input_data['query_result']

          # Determine visualization type
          if self._is_count_query(query):
              return {"type": "text", "data": results}

          elif self._is_listing_query(query):
              return {"type": "table", "data": self._format_table(results)}

          elif self._is_trend_query(query):
              return {
                  "type": "chart",
                  "chart_type": "line",
                  "data": self._format_line_chart(results)
              }

          # ... more conditions ...

  ---
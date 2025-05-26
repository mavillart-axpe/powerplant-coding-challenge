# powerplant-coding-challenge

## How to Launch the Application (Python Implementation)

This section describes the steps to set up and run the production plan API implemented in Python.

1.  **Create and Activate the Virtual Environment**:
    ```bash
    python -m venv env
    # On Windows (PowerShell):
    .\env\Scripts\activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### Run the API Application (Version without CO2 calculation)

This version (`app.py`) does not include the calculation of CO2 emission costs.

3.  **Run the API Application**:
    ```bash
    python app.py
    ```
    The API will run on `http://0.0.0.0:8888` (accessible from `http://localhost:8888`).

4.  **Test the API**:
    ```bash
    curl -X POST -H "Content-Type: application/json" -d @example_payloads/payload1.json http://localhost:8888/productionplan
    ```
    You can use `payload1.json`, `payload2.json`, `payload3.json`, or `payload4.json` for testing.

    This will generate the file `example_payloads/response_{timestamp}_wo_co2.json`.

### Run the API Application (Version with CO2 calculation - Challenge)

This version (`app_challenge.py`) includes the calculation of CO2 emission costs.

3.  **Run the API Application**:
    ```bash
    python app_challenge.py
    ```
    The API will run on `http://0.0.0.0:8888` (accessible from `http://localhost:8888`).

4.  **Test the API**:
    ```bash
    curl -X POST -H "Content-Type: application/json" -d @example_payloads/payload1.json http://localhost:8888/productionplan
    ```
    You can use `payload1.json`, `payload2.json`, `payload3.json`, or `payload4.json` for testing.

    This will generate the file `example_payloads/response_{timestamp}_with_co2.json`.

## How to Launch the Application with Docker

This section describes how to use Docker Compose to run both API versions.

1.  **Build and Run Docker Containers**:
    ```bash
    docker-compose up --build -d
    ```
    This command will build the Docker images for both services and run them in detached mode.

2.  **Access the Applications**:
    *   **Version without CO2 calculation (`app.py`)**: `http://localhost:8888/productionplan`
    *   **Version with CO2 calculation (`app_challenge.py`)**: `http://localhost:8889/productionplan`

3.  **Test the APIs**:
    *   **For `app.py` (no CO2)**:
        ```bash
        curl -X POST -H "Content-Type: application/json" -d @example_payloads/payload1.json http://localhost:8888/productionplan
        ```
    *   **For `app_challenge.py` (with CO2)**:
        ```bash
        curl -X POST -H "Content-Type: application/json" -d @example_payloads/payload1.json http://localhost:8889/productionplan
        ```
    Remember to replace `payload1.json` with `payload2.json`, `payload3.json`, or `payload4.json` as needed.

4.  **Stop and Remove Containers**:
    ```bash
    docker-compose down
    ```
    This command will stop and remove the containers, networks, and volumes created by `up`.
# Preprocessing

This project provides preprocessing tools for preparing data used in fine-tuning open large language models (LLMs).
It is based on Python and Conda virtual environments, and uses a .env file for flexible configuration

---

## Prerequisites

Before you begin, please ensure you have the following installed:

- [Python 3.11+](https://www.python.org/downloads/)
- [Anaconda](https://www.anaconda.com/products/distribution)

> You can check if they're installed by running:
>
> ```bash
> python --version
> conda --version
> ```

---

## Clone the Repository

```bash
git clone https://github.com/Swingft/Preprocessing.git
cd Preprocessing
```

---

## Conda Environment Setup

Follow the steps below to set up the environment using Anaconda.

### 1. Create and Activate the Conda Environment

```bash
conda create -n env_name python=3.11 -y
conda activate env_name
```

> `env_name` can be replaced with any environment name you prefer.

### 2. Install Dependencies

#### Using `environment.yml`

```bash
conda env update --name env_name --file environment.yml --prune
```

---

## .env File Configuration

Create a `.env` file in the root directory and include the following content:

```
OPENAI_API_KEY=your-openai-api-key-here
CLAUDE_API_KEY=your-claude-api-key-here
```

> The `.env` file is used to load environment variables. Refer to the project documentation or `.env.example` for required keys.

---

## How to Run

### Run the Python Script

```bash
python main.py
```

---

## Notes

- Python 3.11 or higher is recommended.
- Using a Conda virtual environment is strongly recommended.
- If the `.env` file is missing or misconfigured, the application may not run properly.

---

## Contact

If you have any questions, please open an issue at [Issues](https://github.com/Swingft/Preprocessing/issues).

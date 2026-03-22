openai-ddg-account-registration v5.0.0
========================================

A Python-based tool for registering ChatGPT accounts using DuckDuckGo 
disposable emails and adding them to sub2api.

Installation
------------

.. code-block:: bash

    pip install -e .

Quick Start
-----------

1. Initialize configuration:

.. code-block:: bash

    python -m scripts.setup

2. Register accounts:

.. code-block:: bash

    python -m scripts.batch_register --count 5

3. Verify accounts:

.. code-block:: bash

    python -m scripts.verify_accounts

4. Cleanup accounts:

.. code-block:: bash

    python -m scripts.cleanup_accounts --status unhealthy

Commands
--------

- ``batch_register``: Register multiple ChatGPT accounts
- ``cleanup_accounts``: Clean up unhealthy or unwanted accounts
- ``verify_accounts``: Verify account status
- ``setup``: Initialize configuration wizard

Configuration
-------------

Edit ``openai-sub2api-config.json`` or run ``setup`` to configure.

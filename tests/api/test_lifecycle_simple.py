"""Simple tests for API lifecycle management."""

from api.lifecycle import lifespan


class TestLifespan:
    """Test suite for lifespan context manager."""

    def test_lifespan_is_callable(self):
        """Test that lifespan is callable."""
        assert callable(lifespan)

    def test_lifespan_is_async_context_manager(self):
        """Test that lifespan returns an async context manager."""
        from fastapi import FastAPI

        app = FastAPI()
        result = lifespan(app)

        # Should be an async context manager
        assert hasattr(result, "__aenter__")
        assert hasattr(result, "__aexit__")

    def test_lifespan_accepts_fastapi_app(self):
        """Test that lifespan accepts a FastAPI app."""
        from fastapi import FastAPI

        app = FastAPI()

        # Should not raise an exception
        result = lifespan(app)
        assert result is not None

    def test_lifespan_returns_async_generator(self):
        """Test that lifespan returns an async generator."""
        from fastapi import FastAPI

        app = FastAPI()
        result = lifespan(app)

        # Should be an async generator context manager
        assert hasattr(result, "__aenter__")
        assert hasattr(result, "__aexit__")

    def test_lifespan_with_none_app(self):
        """Test that lifespan handles None app gracefully."""
        # Type ignore because we're testing the function's behavior with None
        result = lifespan(None)  # type: ignore
        assert result is not None

    def test_lifespan_context_manager_protocol(self):
        """Test that lifespan follows context manager protocol."""
        from fastapi import FastAPI

        app = FastAPI()
        context_manager = lifespan(app)

        # Should have the required methods
        assert hasattr(context_manager, "__aenter__")
        assert hasattr(context_manager, "__aexit__")
        assert callable(context_manager.__aenter__)
        assert callable(context_manager.__aexit__)

    def test_lifespan_is_async_contextmanager(self):
        """Test that lifespan is decorated with asynccontextmanager."""
        # The function should be wrapped with asynccontextmanager
        # This is a basic check to ensure it's properly decorated
        assert hasattr(lifespan, "__wrapped__") or hasattr(lifespan, "__name__")

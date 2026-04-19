# Contributing to AmbientSaga

Thank you for your interest in contributing to AmbientSaga! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md). Together we are building a welcoming and inclusive community.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git

### Development Setup

```bash
# Clone the repository
git clone https://github.com/bingdongni/ambientsaga.git
cd ambientsaga

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install with development dependencies
pip install -e ".[all]"

# Install pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src/ambientsaga --cov-report=html

# Run specific test file
pytest tests/test_world.py -v
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code
ruff format src/ambientsaga/

# Lint code
ruff check src/ambientsaga/

# Type checking
mypy src/ambientsaga/
```

## Project Structure

```
src/ambientsaga/
├── agents/          # Agent system (core, cognition, tier)
├── world/           # World engine (terrain, climate, water, ecology)
├── protocol/        # Emergent interaction protocols
├── evolution/       # Self-evolution system
├── science/         # Unified science framework
├── emergence/      # Emergence systems
├── culture/         # Cultural systems
├── social/         # Social systems
├── natural/        # Natural world systems
├── optimization/   # Performance optimization
├── causal/         # Causal reasoning
├── history/        # Historical tracking
├── visualization/  # Web visualization
├── research/       # Metrics and analysis
└── main.py         # Main entry point
```

## Making Changes

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test updates

Example: `feature/social-stratification`

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
feat(agents): add social stratification system
fix(world): resolve domain coupling initialization issue
docs(readme): update installation instructions
test(science): add tests for physics calculations
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Update documentation if needed
7. Submit a pull request

### Pull Request Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested the changes

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass
```

## Areas for Contribution

### High Priority

- Agent cognitive systems improvements
- Emergence system integration
- Performance optimization
- Bug fixes

### Medium Priority

- Additional scientific domain coupling
- Visualization improvements
- Research tools and metrics
- Documentation improvements

### Lower Priority

- Additional agent tiers
- New terrain generation algorithms
- Extended visualization features

## Questions?

- Open an issue for bug reports
- Start a discussion for questions
- Check existing issues and discussions first

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

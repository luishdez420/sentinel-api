# Security Policy

## Secret Handling

- Do not commit `.env` or any real secret values.
- Use `.env.example` as the template for required environment variables.
- Generate `JWT_SECRET` with at least 32 random characters.
- Rotate any secret that was ever committed or shared outside a trusted runtime.

Example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Pull Request Checks

All pull requests run the GitHub Actions quality workflow before merge. The
workflow currently checks Ruff linting and formatting.

## Reporting Issues

Do not open public issues for sensitive vulnerabilities. Share details privately
with the repository owner.

# Non-secret settings for dev. Secrets come from TF_VAR_* environment variables, never from here.
# Named dev.tfvars, not terraform.tfvars, because .gitignore excludes terraform.tfvars (CLAUDE.md 20).
environment   = "dev"
desired_count = 1
cpu           = 256
memory        = 512
image_tag     = "REPLACE_WITH_GIT_SHA"

output "load_balancer_dns" { value = aws_lb.main.dns_name }
output "backend_registry" { value = aws_ecr_repository.app["backend"].repository_url }
output "frontend_registry" { value = aws_ecr_repository.app["frontend"].repository_url }

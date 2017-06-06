docker-hub-repo = miraco/elastalert
docker-hub-repo-version = $(shell cat .docker-repo-version)
docker-app = elastalert.mira
docker-network = main


docker-network:
	make docker-build
ifeq ($(shell docker network inspect $(docker-network) 2> /dev/null | sed -n 1p), [])
	docker network create $(docker-network)
endif


docker-clean:
ifneq ($(shell docker ps -a -f name=$(docker-app) | sed -n 2p),)
	docker stop $(docker-app)
	docker rm $(docker-app)
endif

docker-build:
	docker build -t $(docker-hub-repo):$(docker-hub-repo-version) .

docker-push:
	make docker-build
	docker build -t $(docker-hub-repo):latest .
	docker push $(docker-hub-repo):$(docker-hub-repo-version)
	docker push $(docker-hub-repo):latest

docker-run:
	make docker-network
	make docker-build
	make docker-clean
	docker run --name $(docker-app) -d $(docker-hub-repo):$(docker-hub-repo-version)

docker-logs:
	make docker-network
	make docker-build
	make docker-clean
	docker run \
		--name $(docker-app) \
		--network $(docker-network) \
		-e ELASTICSEARCH_HOST=elasticsearch-master-0.mira \
		-e ELASTICSEARCH_PORT=9200 \
		-e RUN_EVERY_MINUTES=1 \
		-e RULES_TYPE=api \
		-e RULES_API_HOST=registry-api.mira \
		-e RULES_API_PORT=9092 \
		-e RULES_API_PATH="apps/tester/configs" \
		$(docker-hub-repo):$(docker-hub-repo-version)

docker-bash:
	make docker-run
	docker exec -ti $(docker-app) /bin/bash

IMAGE_NAME=simulation
PORT ?= 8521

build:
	docker build -t $(IMAGE_NAME) .

dev:
	docker run --rm -ti  \
		-v $(PWD)/:/project \
		-p $(PORT):$(PORT) \
		-w '/project' \
		$(IMAGE_NAME)
dev_gui:
	docker run --rm -ti \
		-v $(PWD):/project \
		-p $(PORT):$(PORT) \
		--env="DISPLAY" \
		--env="QT_X11_NO_MITSHM=1" \
		--volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
		-w="/project" \
		$(IMAGE_NAME)

install_mesa:
	cd libs/mesa&&pip3 install -e .

lab:
	docker run --rm -ti  \
		-p $(PORT):$(PORT) \
		-v $(PWD)/:/project \
		-w '/project' \
		$(IMAGE_NAME) \
		jupyter lab --ip=0.0.0.0 --port=$(PORT) --allow-root --no-browser
# AeroSim documentation

The AeroSim documentation is written in [Markdown](https://www.markdownguide.org/) and built using [MkDocs](https://www.mkdocs.org/) with the ReadTheDocs theme. To serve the documentation locally, first [install MkDocs](https://www.mkdocs.org/getting-started/). From the root directory of this repository (one level up from the `docs` folder) run the following command:

```sh
mkdocs serve
```

The documentation will be served on `localhost:8000`. In a web browser, visit `http://localhost:8000/` to view the documentation. If port 8000 is not available, this command will return an error. You can serve the documentation on another port using the following command:

```sh
mkdocs serve -a localhost:5000
```

You can also preview the documentation in GitHub or the MarkDown preview tool for VSCode. In VSCode, right click on the file tab and select *Open Preview*.